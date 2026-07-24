# ADR 0006 — `tenant_id` dès la première version

> **Mise à jour (2026-07-24)** : le « JWT complet différé » de cette décision a
> depuis été **réalisé** — voir [ADR 0009](0009-authentification-jwt-roles.md).
> Le tenant n'est plus lu depuis l'en-tête `X-Tenant-Id` (retiré) mais **dérivé
> du jeton JWT**. Le reste de cette ADR (schéma multi-tenant + RLS) reste valable.

## Contexte

Le produit vise potentiellement plusieurs écoles/institutions. Ajouter le
multi-tenant *a posteriori* sur un schéma existant est risqué (migrations
lourdes, oublis de filtrage). L'authentification complète (JWT par
utilisateur/rôle) n'est en revanche pas nécessaire dès la V1 (usage interne/pilote).

## Décision

`tenant_id` sur **toutes** les tables Postgres dès la première migration (y
compris `messages`/`feedback`, dénormalisé depuis leur parent), lu depuis
l'en-tête `X-Tenant-Id` (défaut `settings.default_tenant`). JWT complet différé.

## Justification

- Retrofit du multi-tenant sur un schéma déjà en production est un projet en
  soi (migration de données, risque de fuite inter-tenant pendant la
  transition) — le coût marginal de l'ajouter dès le départ est faible.
- Dénormaliser `tenant_id` sur `messages`/`feedback` (plutôt que de le déduire
  par jointure sur `conversations`/`messages`) simplifie le filtrage
  applicatif ET les policies RLS (pas de sous-requête corrélée dans chaque
  policy).
- Défense en profondeur à deux niveaux : filtrage explicite dans chaque
  méthode de repository **et** Row Level Security Postgres (policy
  `tenant_isolation`, migration `0002_enable_rls`) — voir aussi le rôle non-
  superuser requis pour que RLS s'applique (`postgres-init/01-app-role.sh`).
- Découpler l'identité du tenant (simple en-tête HTTP) de l'authentification
  utilisateur (JWT) permet de livrer l'isolation multi-tenant sans bloquer sur
  la conception complète du système d'auth/rôles, qui reste un chantier
  distinct.

## Conséquences

- L'en-tête `X-Tenant-Id` n'est aujourd'hui **pas authentifié** — n'importe
  quel client peut prétendre appartenir à n'importe quel tenant. Acceptable
  pour un déploiement pilote/interne, **pas** pour une exposition publique
  sans couche d'authentification devant l'API (JWT, à ajouter avant toute
  mise en production multi-institution réelle).
- Toute nouvelle table devra suivre la même convention (`tenant_id` + index +
  policy RLS) sous peine de rompre l'isolation.
