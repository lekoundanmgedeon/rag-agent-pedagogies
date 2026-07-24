# ADR 0009 — Authentification JWT + rôles (bascule dure)

## Contexte

[ADR 0006](0006-tenant-id-des-le-depart.md) avait livré l'isolation multi-tenant
avec un tenant lu depuis un en-tête `X-Tenant-Id` **non authentifié**, en
différant l'authentification. Le passage à un frontend web à deux espaces
(élève / administration) rend cette authentification nécessaire : distinguer les
rôles, prouver l'identité, et empêcher un client de se déclarer tenant ou élève
arbitraire.

## Décision

Authentification **JWT obligatoire** sur toutes les routes métier (bascule dure,
sans mode déclaratif transitoire ; seul `/health` reste public). L'en-tête
`X-Tenant-Id` est **retiré** — tenant et identité sont dérivés du jeton.

- Table `users` (migration `0005_add_users`), **hors RLS** (le login cherche par
  email avant de connaître le tenant), email **unique global**, rôle
  `admin | student`, `student_id` reliant un compte élève à l'identifiant du cœur.
- Mots de passe hachés **bcrypt** ; jetons **JWT HS256** signés avec `JWT_SECRET`
  (`api/security.py`, dataclass `Principal`).
- Routes `api/routes/auth.py` : `login`, `me`, `users` (création/liste, admin).
- Dépendances : `get_current_user` (décode le `Bearer`), `get_tenant_id` (dérivé
  du jeton), `require_admin`, `get_optional_user` (pour `/health`).
- Autorisation : espace admin (`documents`, `search`, `logs`) réservé au rôle
  admin ; chat/conversations/progression cloisonnés à l'identité de l'élève.

## Justification

- **Bascule dure plutôt qu'un flag `AUTH_ENABLED`** : un mode optionnel aurait
  laissé deux chemins de sécurité à maintenir et tester, et un défaut non
  authentifié exploitable par erreur de configuration. La suite de tests API a
  été réécrite en conséquence (jetons forgés en test, comptes réels seedés pour
  les tests de login) — coût ponctuel accepté pour un modèle de sécurité unique.
- **`users` hors RLS** : le login précède la connaissance du tenant ; mettre la
  table sous RLS créerait une dépendance circulaire (il faut le tenant pour lire
  la ligne qui donne le tenant). Email unique global lève l'ambiguïté au login.
- **Identité prouvée, plus déclarée** : `get_tenant_id` et le `student_id`
  effectif viennent du jeton signé, fermant l'usurpation de tenant/élève que
  l'ADR 0006 assumait comme dette.

## Conséquences

- Aucun compte par défaut : amorcer le premier admin via `scripts/create_user.py`
  (ou le profil `seed` du docker-compose) — sans cela, personne ne peut se
  connecter. C'est volontaire (pas de compte/mot de passe en dur).
- `JWT_SECRET` doit être fort et **stable** entre redémarrages (un secret changé
  invalide tous les jetons émis). En production, ≥ 32 octets.
- Le frontend Streamlit initial, qui n'envoie pas de jeton, devient inutilisable
  — cohérent avec son remplacement par le SPA Vue (`agent-tuteur-web/`).
- Gaps résiduels assumés : pas de refresh token ni de réinitialisation de mot de
  passe en self-service (jeton unique, expiration `JWT_EXPIRY_HOURS`, 7 j par
  défaut ; régénération par un admin via `/api/auth/users`).
