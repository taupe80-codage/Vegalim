#!/usr/bin/env python3
"""
api_keys.py — Gestion des comptes et clés API B2B en ligne de commande.

Usage :
    python scripts/api_keys.py create EMAIL [--plan free|starter|pro] [--expires-days N]
    python scripts/api_keys.py list [--email EMAIL]
    python scripts/api_keys.py revoke ID_CLE            # préfixe affiché par `list`
    python scripts/api_keys.py revoke --email EMAIL     # toutes les clés du compte
    python scripts/api_keys.py plan EMAIL PLAN

La clé brute n'est affichée qu'à la création (seul son SHA-256 est stocké).
Les routes /admin/* exigent en plus que l'email figure dans ADMIN_EMAILS.

Base utilisée : DATABASE_URL du fichier .env (SQLite alim_dev.db sinon).
Le schéma doit être à jour (`alembic upgrade head`, fait au démarrage de l'API).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")  # avant l'import de la session : DATABASE_URL lue à l'import
except ImportError:
    pass

from backend.db.models import ApiKey, ApiUser  # noqa: E402
from backend.db.repositories import ApiKeyRepository, ApiUserRepository  # noqa: E402
from backend.db.session import DATABASE_URL, db_session  # noqa: E402
from backend.engine.auth_middleware import PLANS  # noqa: E402

ID_LEN = 12


def _admin_emails() -> set[str]:
    from backend.core.config import settings
    return settings.admin_emails


def _norm(email: str) -> str:
    return email.strip().lower()


def cmd_create(args) -> int:
    email = _norm(args.email)
    with db_session() as db:
        users = ApiUserRepository(db)
        user = users.get_by_email(email) or users.create(email, args.plan)
        if user.plan != args.plan and args.plan_explicit:
            users.upgrade_plan(user.user_id, args.plan)
        raw_key, key = ApiKeyRepository(db).generate(user.user_id, args.expires_days)
        plan, key_id = user.plan, key.key_hash[:ID_LEN]
    print(f"Compte  : {email} (plan {plan})")
    print(f"ID clé  : {key_id}")
    print(f"Clé API : {raw_key}")
    print("\nConservez cette clé : elle ne sera plus jamais affichée.")
    print("En-tête HTTP : X-API-Key: <clé>")
    if email not in _admin_emails():
        print("Note : email absent de ADMIN_EMAILS — pas d'accès /admin/*.")
    return 0


def cmd_list(args) -> int:
    now = datetime.now(timezone.utc)
    with db_session() as db:
        q = db.query(ApiUser, ApiKey).outerjoin(ApiKey, ApiKey.user_id == ApiUser.user_id)
        if args.email:
            q = q.filter(ApiUser.email == _norm(args.email))
        rows = q.order_by(ApiUser.email, ApiKey.created_at).all()
        if not rows:
            print("Aucun compte API.")
            return 0
        admins = _admin_emails()
        print(f"{'EMAIL':<32} {'PLAN':<8} {'ADMIN':<5} {'ID CLÉ':<{ID_LEN}}  {'ÉTAT':<8} CRÉÉE LE")
        for user, key in rows:
            admin = "oui" if user.email in admins else ""
            if key is None:
                print(f"{user.email:<32} {user.plan:<8} {admin:<5} {'—':<{ID_LEN}}")
                continue
            expires = key.expires_at
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            state = "active" if key.is_active else "révoquée"
            if key.is_active and expires is not None and expires < now:
                state = "expirée"
            created = key.created_at.strftime("%Y-%m-%d") if key.created_at else ""
            print(f"{user.email:<32} {user.plan:<8} {admin:<5} {key.key_hash[:ID_LEN]:<{ID_LEN}}  {state:<8} {created}")
    return 0


def cmd_revoke(args) -> int:
    if bool(args.key_id) == bool(args.email):
        print("Indiquer soit un ID de clé, soit --email.", file=sys.stderr)
        return 2
    with db_session() as db:
        q = db.query(ApiKey).filter(ApiKey.is_active.is_(True))
        if args.email:
            user = ApiUserRepository(db).get_by_email(_norm(args.email))
            if not user:
                print(f"Compte API introuvable : {args.email}", file=sys.stderr)
                return 1
            keys = q.filter(ApiKey.user_id == user.user_id).all()
        else:
            if len(args.key_id) < 6:
                print("ID de clé trop court (6 caractères minimum).", file=sys.stderr)
                return 2
            keys = q.filter(ApiKey.key_hash.startswith(args.key_id.lower())).all()
            if len(keys) > 1:
                print("ID ambigu : plusieurs clés correspondent, allonger le préfixe.", file=sys.stderr)
                return 2
        for key in keys:
            key.is_active = False
    if not keys:
        print("Aucune clé active correspondante.", file=sys.stderr)
        return 1
    print(f"{len(keys)} clé(s) révoquée(s).")
    return 0


def cmd_plan(args) -> int:
    with db_session() as db:
        users = ApiUserRepository(db)
        user = users.get_by_email(_norm(args.email))
        if not user:
            print(f"Compte API introuvable : {args.email}", file=sys.stderr)
            return 1
        users.upgrade_plan(user.user_id, args.plan)
    print(f"{args.email} → plan {args.plan}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gestion des clés API B2B")
    sub = parser.add_subparsers(dest="command", required=True)
    plans = sorted(PLANS)

    p = sub.add_parser("create", help="créer une clé (et le compte si absent)")
    p.add_argument("email")
    p.add_argument("--plan", choices=plans, default=None)
    p.add_argument("--expires-days", type=int, default=None)
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("list", help="lister comptes et clés")
    p.add_argument("--email")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("revoke", help="révoquer une clé ou toutes celles d'un compte")
    p.add_argument("key_id", nargs="?")
    p.add_argument("--email")
    p.set_defaults(func=cmd_revoke)

    p = sub.add_parser("plan", help="changer le plan d'un compte")
    p.add_argument("email")
    p.add_argument("plan", choices=plans)
    p.set_defaults(func=cmd_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "create":
        args.plan_explicit = args.plan is not None
        args.plan = args.plan or "free"
    try:
        return args.func(args)
    except Exception as exc:  # table absente, base injoignable…
        detail = str(getattr(exc, "orig", None) or exc).splitlines()[0]
        print(f"Erreur base de données ({DATABASE_URL.split('@')[-1]}) : {detail}", file=sys.stderr)
        print("Schéma à jour ? → python -m alembic upgrade head", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
