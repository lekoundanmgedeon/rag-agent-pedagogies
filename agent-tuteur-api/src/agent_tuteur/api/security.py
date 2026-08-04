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


#: Durée de validité d'un quiz remis à un élève. Assez long pour réfléchir,
#: assez court pour qu'un jeton ne traîne pas indéfiniment.
QUIZ_TOKEN_MINUTES = 60


def create_quiz_token(*, competence: str, correct_answer: str, explanation: str) -> str:
    """Scelle la correction d'un quiz dans un jeton signé remis à l'élève.

    **Pourquoi ce détour.** La bonne réponse ne doit pas descendre dans le
    navigateur avec le quiz : un élève qui ouvre les outils de développement la
    lirait avant de répondre, et l'évaluation ne mesurerait plus rien. Elle
    voyage donc **signée** : le client la transporte sans pouvoir la lire ni la
    modifier, et la route de correction la rouvre côté serveur.

    C'est l'alternative sans état à une table de quiz en base — voir le point
    V6 de JOURNAL_FUSION.md pour l'arbitrage laissé ouvert.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "competence": competence,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "iat": now,
        "exp": now + timedelta(minutes=QUIZ_TOKEN_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_quiz_token(token: str) -> dict:
    """Rouvre un jeton de quiz, ou lève ``AuthError`` (signature/expiration)."""
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthError(f"Quiz expiré ou invalide : {exc}") from exc
    try:
        return {
            "competence": claims["competence"],
            "correct_answer": claims["correct_answer"],
            "explanation": claims.get("explanation", ""),
        }
    except KeyError as exc:
        raise AuthError(f"Jeton de quiz incomplet : champ manquant {exc}") from exc
