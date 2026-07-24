"""Authentification : login (émission JWT), profil courant, création de comptes.

Le login est la seule route qui accède à la base **sans tenant** (recherche par
email avant de connaître le tenant — table ``users`` hors RLS, cf.
``persistence/models.py::User``). Les routes ``/me`` et ``/users`` exigent un
jeton valide ; la création de comptes est réservée aux administrateurs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agent_tuteur.api.dependencies import get_current_user, require_admin, user_repo
from agent_tuteur.api.schemas import CreateUserRequest, LoginRequest, TokenOut, UserOut
from agent_tuteur.api.security import Principal, create_access_token, hash_password, verify_password
from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.persistence.repositories import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])
_logger = get_logger("agent_tuteur.api.routes.auth")


def _principal_of(user) -> Principal:  # noqa: ANN001 - User ORM
    return Principal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
        student_id=user.student_id,
    )


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginRequest, users: UserRepository = Depends(user_repo)) -> TokenOut:
    user = await users.get_by_email(payload.email)
    # Message identique compte inexistant / mauvais mot de passe : pas d'oracle
    # permettant d'énumérer les emails valides.
    if user is None or not verify_password(payload.password, user.password_hash):
        log_event(_logger, "auth:login_failed", email=payload.email, log_level=30)
        raise HTTPException(status_code=401, detail="Identifiants invalides.")

    token = create_access_token(_principal_of(user))
    log_event(_logger, "auth:login_ok", user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(
    principal: Principal = Depends(get_current_user),
    users: UserRepository = Depends(user_repo),
) -> UserOut:
    """Profil de l'utilisateur courant — permet au front de restaurer la session."""
    user = await users.get_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Compte introuvable.")
    return UserOut.model_validate(user)


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    admin: Principal = Depends(require_admin),
    users: UserRepository = Depends(user_repo),
) -> UserOut:
    """Crée un compte (élève ou admin) dans le tenant de l'administrateur courant."""
    existing = await users.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email.")

    user = await users.create(
        tenant_id=admin.tenant_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        student_id=payload.student_id,
        display_name=payload.display_name,
    )
    log_event(_logger, "auth:user_created", user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    return UserOut.model_validate(user)


@router.get("/users", response_model=list[UserOut])
async def list_users(
    admin: Principal = Depends(require_admin),
    users: UserRepository = Depends(user_repo),
) -> list[UserOut]:
    """Liste les comptes du tenant de l'administrateur courant."""
    rows = await users.list_for_tenant(admin.tenant_id)
    return [UserOut.model_validate(u) for u in rows]
