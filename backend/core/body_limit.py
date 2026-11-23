"""
body_limit.py — Taille maximale des corps de requête (middleware ASGI).

Sans limite, n'importe quelle route JSON acceptait un corps de plusieurs
centaines de Mo, lu entièrement en mémoire (et l'envoi de photo aussi quand
le client n'annonçait pas sa taille) : un seul client pouvait saturer la
mémoire du serveur (revue de sécurité du 2026-11-23).

- Content-Length annoncé trop grand → 413 immédiat, corps non lu.
- Corps envoyé en flux (chunked) → compté au fil de la lecture, 413 dès le
  dépassement.
"""
from __future__ import annotations

import json
import re

from fastapi import HTTPException

DEFAULT_LIMIT = 1 * 1024 * 1024            # 1 Mo : formulaires, recettes, avis
PHOTO_LIMIT = 9 * 1024 * 1024              # photo de recette (8 Mo + marge)
_PHOTO_PATH = re.compile(r"^/contributions/[^/]+/photo$")


def limit_for(method: str, path: str) -> int:
    if method == "PUT" and _PHOTO_PATH.match(path):
        return PHOTO_LIMIT
    return DEFAULT_LIMIT


class _TooLarge(HTTPException):
    """HTTPException : FastAPI la relaie telle quelle pendant la lecture du corps
    (une autre exception y devient « 400 erreur d'analyse »)."""

    def __init__(self, limit: int):
        super().__init__(status_code=413,
                         detail=f"Requête trop volumineuse ({limit // (1024 * 1024)} Mo au plus).")


class BodySizeLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)
        limit = limit_for(scope["method"], scope.get("path", ""))
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > limit:
                        return await self._reject(send, limit)
                except ValueError:
                    return await self._reject(send, limit)
        received = 0
        started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _TooLarge(limit)
            return message

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _TooLarge:
            if not started:
                await self._reject(send, limit)

    @staticmethod
    async def _reject(send, limit: int):
        body = json.dumps({"detail": f"Requête trop volumineuse ({limit // (1024 * 1024)} Mo au plus)."},
                          ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
