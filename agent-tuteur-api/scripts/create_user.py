"""Crée un compte (admin ou élève) en base — amorçage initial de l'authentification.

Aucun compte n'est câblé en dur : le premier administrateur se crée avec ce
script, puis les comptes suivants peuvent l'être depuis l'espace admin
(``POST /api/auth/users``).

    PYTHONPATH=src python scripts/create_user.py \
        --email admin@ecole.sn --password 'secret' --role admin --tenant default

Pour un élève, préciser ``--student-id`` (lien vers l'identifiant utilisé par le
cœur : progression, conversations) :

    PYTHONPATH=src python scripts/create_user.py \
        --email eleve1@ecole.sn --password 'secret' --role student \
        --student-id eleve1 --tenant default
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agent_tuteur.api.security import hash_password
from agent_tuteur.config.settings import get_settings
from agent_tuteur.persistence.db import dispose_engine, init_engine, session_scope
from agent_tuteur.persistence.repositories import UserRepository


async def _create(args: argparse.Namespace) -> int:
    settings = get_settings()
    init_engine(settings.database_url)
    try:
        # Session sans tenant : la table users est hors RLS (cf. models.User).
        async with session_scope(None) as session:
            repo = UserRepository(session)
            if await repo.get_by_email(args.email) is not None:
                print(f"⚠️  Un compte existe déjà avec l'email {args.email}.", file=sys.stderr)
                return 1
            user = await repo.create(
                tenant_id=args.tenant,
                email=args.email,
                password_hash=hash_password(args.password),
                role=args.role,
                student_id=args.student_id,
                display_name=args.display_name,
            )
        print(f"✅ Compte créé : {user.email} (rôle={user.role}, tenant={user.tenant_id}, id={user.id})")
        return 0
    finally:
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser(description="Créer un compte utilisateur (admin/élève).")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", choices=["admin", "student"], default="admin")
    parser.add_argument("--tenant", default=get_settings().default_tenant)
    parser.add_argument("--student-id", dest="student_id", default=None)
    parser.add_argument("--display-name", dest="display_name", default=None)
    args = parser.parse_args()
    if args.role == "student" and not args.student_id:
        args.student_id = args.email.split("@")[0]
    return asyncio.run(_create(args))


if __name__ == "__main__":
    sys.exit(main())
