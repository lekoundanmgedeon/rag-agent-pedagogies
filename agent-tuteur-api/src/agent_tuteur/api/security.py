"""Primitives d'authentification : hachage de mot de passe et jetons JWT.

Ce module ne connaît ni FastAPI, ni la base : il ne fait que hacher/vérifier des
mots de passe (``bcrypt``) et signer/décoder des jetons (``pyjwt``, HS256 avec le
``jwt_secret`` des settings). Les dépendances HTTP (extraction du header
``Authorization``, 401/403) vivent dans ``api/dependencies.py`` ; les routes de
login dans ``api/routes/auth.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from agent_tuteur.config.settings import get_settings

#: bcrypt tronque au-delà de 72 octets et lève depuis la v4 — on borne
#: explicitement l'entrée pour un comportement déterministe.
_BCRYPT_MAX_BYTES = 72


class AuthError(Exception):
    """Jeton invalide, expiré ou absent — traduit en HTTP 401 par la couche API."""


@dataclass(frozen=True)
class Principal:
    """Identité authentifiée dérivée d'un JWT valide.

    ``student_id`` est le lien vers l'identifiant élève déjà utilisé partout dans
    le cœur (progression, conversations, audit). ``None`` pour un admin qui n'est
    pas rattaché à un parcours élève.
    """

    user_id: str
    tenant_id: str
    role: str
    email: str
    student_id: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def hash_password(password: str) -> str:
    """Hache un mot de passe en clair (bcrypt, sel aléatoire intégré)."""
    payload = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(payload, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe en clair contre son hash bcrypt (temps constant)."""
    try:
        payload = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(payload, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(principal: Principal) -> str:
    """Signe un JWT portant l'identité complète (tenant + rôle + student_id)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": principal.user_id,
        "tenant_id": principal.tenant_id,
        "role": principal.role,
        "email": principal.email,
        "student_id": principal.student_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Principal:
    """Décode et vérifie un JWT, ou lève ``AuthError`` (signature/expiration/forme)."""
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthError(f"Jeton invalide : {exc}") from exc

    try:
        return Principal(
            user_id=claims["sub"],
            tenant_id=claims["tenant_id"],
            role=claims["role"],
            email=claims["email"],
            student_id=claims.get("student_id"),
        )
    except KeyError as exc:
        raise AuthError(f"Jeton incomplet : champ manquant {exc}") from exc
