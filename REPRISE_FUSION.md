# Historique d'avancement de la fusion — archive

> **⚠️ Ce document n'est plus le point de reprise.**
>
> Il a servi de fil conducteur pendant l'exécution de la fusion, du 3 au 4 août
> 2026, alors que le travail vivait sur la branche `feat/fusion`. **Cette branche
> a été fusionnée dans `main`** le 2026-08-06 (commit de merge `064db7e`), et son
> contenu est décrit ailleurs.
>
> **Pour reprendre le travail, lire [`docs/STATUS.md`](docs/STATUS.md)** — c'est
> le point de reprise unique et maintenu : état vérifié, commandes, ce qu'il
> reste à faire, pièges connus.
>
> Ce fichier est conservé pour la trace de l'avancement module par module : le
> rythme des commits, l'évolution du nombre de tests, et les règles de travail
> qui ont été suivies. Il n'est plus mis à jour.

Autres documents de la fusion :

- [`JOURNAL_FUSION.md`](JOURNAL_FUSION.md) — le détail de chaque décision, une
  section par module, plus les « ⚠️ Points à valider ».
- [`docs/RAPPORT_FUSION.md`](docs/RAPPORT_FUSION.md) — la version courte, pour la
  réunion technique.
- [`docs/adr/0010-fusion-nuru-ats.md`](docs/adr/0010-fusion-nuru-ats.md) — la
  décision d'architecture, avec en annexe le devenir des 13 points de dette
  recensés par NURU.
- [`docs/COMPARATIF_ARCHITECTURES.md`](docs/COMPARATIF_ARCHITECTURES.md) §7.2 —
  le plan d'origine.

---

## 1. Le fil des commits

La fusion s'est faite en 14 commits sur `feat/fusion`, un module à la fois :

```
1ddb6a7  M7  documentations fusionnées, journal complété
6fee1aa  M7  intégration continue + analyse statique
6330277  (commit intermédiaire)
9d49ed5  (résumé final du journal)
4664114  M6  GeminiLLM et chaîne de repli configurable
a946e46  M5  routes quiz, évaluation et maîtrise
4a19f94  (document de reprise)
b9cb9a8  M5  règle d'accès centralisée + tests 401/403
f426c02  M4  branche quiz, vérification déterministe, suivi de maîtrise
1e3f005  M3  modèle de données pédagogique et rôles étendus
2d9532a  M2  re-ranker cours/complément au-dessus du RRF
b28d1a4  M1  parsing PDF PyMuPDF + extracteurs de métadonnées
cab7ecf  (départ, sur main)
```

Puis, après le merge dans `main` :

```
9859a75  fix: les épinglages doivent tenir sur Python 3.11, pas seulement 3.12
cbd043c  chore: ne pas versionner tsconfig.tsbuildinfo
064db7e  Merge branch 'feat/fusion' — fusion des dépôts NURU et ATS
afa2993  docs: JOURNAL_FUSION en .docx + deux corrections de rendu
517b090  docs: rapport de fusion pour la réunion technique (+ livrable Word)
9146ba2  docs: REPRISE_FUSION après le frontend
9a1cba7  frontend(P5): nouveau frontend Next.js 16 / React 19 / TypeScript
```

> Le module 8 (frontend Next.js, phase P5 du plan) a été traité **après** le
> module 7, d'où sa position dans l'historique : la consolidation portait sur le
> backend, et le frontend a été porté ensuite contre l'API déjà stabilisée.

## 2. Avancement par module

| Module | Sujet | État |
|---|---|---|
| M0 | Branche, journal, mesure de référence | ✅ terminé |
| M1 | Lecture des PDF + métadonnées (phase P1 du plan) | ✅ terminé |
| M2 | Priorité au cours dans la recherche (P2) | ✅ terminé |
| M3 | Modèle de données pédagogique + rôles (P3.1-P3.2) | ✅ terminé |
| M4 | Quiz, vérification, maîtrise (P3.3-P3.5) | ✅ terminé |
| M5 | Routes API (P4) | ✅ terminé |
| M6 | Gemini + chaîne LLM configurable (P6) | ✅ terminé |
| M7 | Consolidation : ADR, épinglages, ruff, CI (P7) | ✅ terminé |
| M8 | Frontend Next.js — 9 écrans, types générés (P5) | ✅ terminé |
| — | Bascule du déploiement vers le nouveau frontend | ⬜ **décision V7** |

## 3. Évolution du nombre de tests

Aucun module n'a jamais fait baisser ce nombre — c'était une règle de travail.

| Étape | Sans base de données | Avec PostgreSQL |
|---|---|---|
| Départ | 145 | — |
| Après M1 | 177 | — |
| Après M2 | 195 | — |
| Après M3 | 235 | 286 |
| Après M4 | 290 | 341 |
| Après M5 | 290 | 386 |
| **Après M7** | **317** | **413** |

> Le total « sans base » ne bouge pas au module 5 : les tests ajoutés sont des
> tests d'API, qui exigent PostgreSQL et sont donc ignorés sans lui.

## 4. Ce qui a été fait, en bref

*(le détail est dans `JOURNAL_FUSION.md`, une section par module)*

- **M1** — PyMuPDF remplace `pypdf` pour lire les PDF (les formules étaient
  détruites). Trois extracteurs de métadonnées portés de NURU. Vérifié sur les
  103 PDF réels : aucune erreur de lecture.
- **M2** — La recherche remonte maintenant le **cours** en tête quand l'élève
  demande une explication, et l'agent **avoue** quand le corpus n'a que des TD
  au lieu d'inventer un cours.
- **M3** — Cinq tables portées de NURU (maîtrise, résultats, badges,
  recommandations, liaisons). Migrations vérifiées sur PostgreSQL réel, aller
  **et** retour. Trois tables de NURU supprimées car en doublon.
- **M4** — L'agent sait **interroger** l'élève (troisième posture, à côté de
  « exercice » et « cours »), **vérifier** ce qu'il produit, et **enregistrer**
  les réussites.
- **M5** — Les routes `/api/quiz`, `/api/quiz/answer`, `/api/evaluation/{id}` et
  `/api/mastery/{id}`, toutes protégées. La règle « qui a le droit de voir quel
  élève » est écrite une seule fois. **Une faille a été refermée au passage** :
  les rôles ajoutés au M3 laissaient un parent consulter n'importe quel élève.
  Et la bonne réponse d'un quiz ne descend plus dans le navigateur.
- **M6** — Gemini ajouté comme fournisseur, et l'ordre de la chaîne de repli
  devient un réglage `.env` (`LLM_CHAIN`). Changer de modèle ne demande plus
  aucune modification de code.
- **M7** — ADR 0010, dépendances épinglées, analyse statique configurée, et
  **intégration continue**. Un défaut réel trouvé au passage : `zip()` sans
  garde à l'indexation laissait des morceaux non indexés en silence.
- **M8** — Frontend Next.js/TypeScript, 9 écrans, avec le **contrat d'API
  généré depuis OpenAPI** : renommer un champ côté API casse la compilation
  (vérifié en le simulant). Vérifié de bout en bout contre une vraie API :
  connexion, garde de route, boucle quiz, streaming SSE.

## 5. Les règles de travail qui ont été suivies

Elles sont reprises et maintenues dans [`docs/STATUS.md`](docs/STATUS.md) §6.

1. **Un module à la fois**, jamais de fusion en bloc.
2. **Après chaque module** : la suite de tests passe, et le nombre de tests ne
   diminue jamais.
3. **Les tests unitaires ne suffisent pas** — chaque module a été vérifié contre
   l'infrastructure réelle (les 103 PDF, PostgreSQL). C'est ainsi que la faille
   d'accès du M5 et l'erreur de classement du M2 ont été trouvées.
4. **Documenter dans `JOURNAL_FUSION.md`** au fur et à mesure, en langage simple :
   ce qui est gardé, retiré, ajouté, et l'impact.
5. **Ne rien trancher seul** sur un point non prévu par le plan : l'ajouter à
   « ⚠️ Points à valider » avec les options et un avis argumenté.
6. **Ne jamais toucher aux conteneurs Docker** qui ne sont pas à nous.
