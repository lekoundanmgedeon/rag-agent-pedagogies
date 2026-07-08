"""Limiteur de débit partagé (slowapi) — une seule instance pour toute l'app.

Clé par adresse IP cliente. Appliqué explicitement sur ``/api/chat`` et
``/api/upload`` (routes coûteuses : appel LLM, ingestion) via ``@limiter.limit``.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
