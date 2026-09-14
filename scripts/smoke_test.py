#!/usr/bin/env python3
"""
smoke_test.py — Test de fumée d'une API ALIM démarrée (production ou recette).

Rejoue un parcours complet contre une instance réelle : santé, sécurité,
compte, recettes, personnalisation, suppression RGPD. Crée un compte jetable
(email unique) et le supprime à la fin — relançable à volonté.

Usage :
    python scripts/smoke_test.py --base-url http://127.0.0.1:8000
    python scripts/smoke_test.py --base-url https://mondomaine.com \\
        --metrics-token "$METRICS_TOKEN" --expect-production

Code de sortie : 0 si tout passe, 1 sinon.

Né du test de production du 2026-09-14, qui a trouvé des bugs invisibles pour
pytest sous SQLite : interactions refusées (recipe_id int), logs applicatifs
muets après la migration, migrations concurrentes entre workers.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid


class Smoke:
    def __init__(self, base_url: str, insecure: bool = False):
        self.base = base_url.rstrip("/")
        self.ctx = ssl._create_unverified_context() if insecure else None
        self.failures: list[str] = []
        self.token: str | None = None

    # ── HTTP ──────────────────────────────────────────────────────────────────
    def call(self, method: str, path: str, body=None, headers=None, auth=False):
        h = {"Content-Type": "application/json", **(headers or {})}
        if auth and self.token:
            h["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, method=method, data=data, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=60, context=self.ctx) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    @staticmethod
    def json_of(raw: bytes):
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            return None

    # ── Assertions ────────────────────────────────────────────────────────────
    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        print(f"{'OK ' if ok else 'KO '} {name}{'' if ok or not detail else ' — ' + detail}")
        if not ok:
            self.failures.append(name)
        return ok

    def expect(self, name: str, res, statuses) -> bytes:
        status, raw = res
        self.check(f"{name} → {status}", status in statuses,
                   f"attendu {sorted(statuses)} : {raw[:160].decode('utf-8', 'replace')}")
        return raw

    def wait_ready(self, timeout_s: int) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                if self.call("GET", "/healthz")[0] == 200:
                    return True
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(1)
        return False


def run(args) -> int:
    s = Smoke(args.base_url, insecure=args.insecure)
    if not s.check(f"API joignable ({s.base})", s.wait_ready(args.wait)):
        return 1

    # ── Santé et surface publique ─────────────────────────────────────────────
    health = s.json_of(s.expect("GET /healthz", s.call("GET", "/healthz"), {200})) or {}
    checks = health.get("checks", {})
    s.check("healthz : base de données ok", checks.get("database", {}).get("status") == "ok", str(checks))
    s.check("healthz : recettes chargées", (checks.get("recipes", {}).get("count") or 0) > 0, str(checks))

    if args.expect_production:
        s.expect("GET /docs fermé en production", s.call("GET", "/docs"), {404})
        s.expect("GET /metrics sans jeton", s.call("GET", "/metrics"), {401, 403})
    if args.metrics_token:
        s.expect("GET /metrics avec jeton",
                 s.call("GET", "/metrics", headers={"X-Metrics-Token": args.metrics_token}), {200})

    if not args.skip_ui:
        html = s.expect("GET /ui", s.call("GET", "/ui"), {200})
        bundle = re.search(rb'src="(/assets/[^"]+\.js)"', html)
        if s.check("/ui référence un bundle JS", bool(bundle)):
            status, js = s.call("GET", bundle.group(1).decode())
            s.check("bundle JS sans URL d'API codée en dur",
                    status == 200 and b"localhost:8000" not in js and b"mondomaine" not in js)

    # ── Sécurité des routes protégées ────────────────────────────────────────
    s.expect("PUT /planning/prices sans jeton", s.call("PUT", "/planning/prices/tofu", {"price": 3}), {401})
    s.expect("GET /admin/api_stats sans clé", s.call("GET", "/admin/api_stats"), {401})
    s.expect("GET /profil/likes sans jeton", s.call("GET", "/profil/likes"), {401})

    # ── Compte ────────────────────────────────────────────────────────────────
    email = f"smoke-{uuid.uuid4().hex[:12]}@example.com"
    password = f"Smoke-{uuid.uuid4().hex}-Aa1!"
    s.expect("POST /auth/register", s.call("POST", "/auth/register", {"email": email, "password": password}), {200, 201})
    login = s.json_of(s.expect("POST /auth/login",
                               s.call("POST", "/auth/login", {"email": email, "password": password}), {200})) or {}
    s.token = login.get("access_token")
    if not s.check("jeton JWT reçu", bool(s.token)):
        return _summary(s)

    if args.expect_production:
        raw = s.expect("POST /auth/forgot-password", s.call("POST", "/auth/forgot-password", {"email": email}), {200, 202, 429})
        s.check("jeton de réinitialisation non exposé", b"reset_token\":\"" not in raw.replace(b" ", b""))

    try:
        # ── Recettes ─────────────────────────────────────────────────────────
        top = s.json_of(s.expect("GET /recettes/top", s.call("GET", "/recettes/top"), {200}))
        items = top if isinstance(top, list) else ((top or {}).get("recipes") or (top or {}).get("results") or [])
        ids = [r["id"] for r in items if isinstance(r, dict) and r.get("id")]
        s.check("/recettes/top non vide", len(ids) >= 5, f"{len(ids)} recettes")
        if ids:
            s.expect("GET /recettes/{id}", s.call("GET", f"/recettes/{ids[0]}", auth=True), {200})
        s.expect("POST /recettes/recommend", s.call("POST", "/recettes/recommend", {"limit": 5}, auth=True), {200})

        # ── Personnalisation (identifiants textuels, like idempotent) ───────
        for rid in ids[:5]:
            s.expect(f"like {rid}", s.call("POST", "/profil/interaction",
                                           {"recipe_id": rid, "action": "like"}, auth=True), {204})
        if ids:
            s.call("POST", "/profil/interaction", {"recipe_id": ids[0], "action": "like"}, auth=True)
            s.expect("vue", s.call("POST", "/profil/interaction", {"recipe_id": ids[0], "action": "view"}, auth=True), {204})
            s.expect("recette inconnue → 404", s.call("POST", "/profil/interaction",
                                                      {"recipe_id": "n_existe_pas", "action": "like"}, auth=True), {404})
        likes = (s.json_of(s.expect("GET /profil/likes", s.call("GET", "/profil/likes", auth=True), {200})) or {}).get("liked", [])
        s.check("likes sans doublon", sorted(likes) == sorted(set(ids[:5])), str(likes))
        if len(ids) >= 5:
            s.call("POST", "/profil/interaction", {"recipe_id": ids[4], "action": "unlike"}, auth=True)
            likes = (s.json_of(s.call("GET", "/profil/likes", auth=True)[1]) or {}).get("liked", [])
            s.check("unlike retire le favori", ids[4] not in likes and len(likes) == 4, str(likes))
            s.call("POST", "/profil/interaction", {"recipe_id": ids[4], "action": "like"}, auth=True)
            learning = s.json_of(s.expect("GET /profil/learning", s.call("GET", "/profil/learning", auth=True), {200})) or {}
            s.check("personnalisation active après 5 likes", learning.get("personalization_active") is True, str(learning)[:160])
    finally:
        # ── Suppression RGPD (toujours, même après un échec) ────────────────
        s.expect("DELETE /auth/account", s.call("DELETE", "/auth/account", auth=True), {200, 204})
        s.expect("jeton refusé après suppression", s.call("GET", "/profil/likes", auth=True), {401, 404})

    return _summary(s)


def _summary(s: Smoke) -> int:
    print()
    if s.failures:
        print(f"ÉCHEC : {len(s.failures)} contrôle(s) — " + " | ".join(s.failures))
        return 1
    print("Tous les contrôles passent.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Test de fumée d'une API ALIM démarrée")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--metrics-token", default="")
    p.add_argument("--expect-production", action="store_true",
                   help="vérifie aussi /docs fermé, /metrics protégé, jeton de reset non exposé")
    p.add_argument("--skip-ui", action="store_true", help="ne pas vérifier /ui (frontend non compilé)")
    p.add_argument("--insecure", action="store_true", help="accepter un certificat HTTPS non vérifié (localhost)")
    p.add_argument("--wait", type=int, default=90, help="secondes d'attente du démarrage")
    return run(p.parse_args(argv))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
