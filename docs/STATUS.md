# État de reprise — Agent Tuteur Sénégal

*Dernière mise à jour : 2026-07-10. Point de reprise pour une nouvelle session
(humaine ou Claude) — pas une doc de référence finale (voir index ci-dessous).*

## Où trouver quoi (ne pas dupliquer ici)

| Besoin | Document |
|---|---|
| Vue d'ensemble, démarrage rapide | [`README.md`](../README.md) (racine) |
| Architecture, flux, frontières | [`docs/architecture.md`](architecture.md) |
| Chaque endpoint de l'API | [`docs/api.md`](api.md) |
| Décisions techniques argumentées | [`docs/RAPPORT_TECHNIQUE.md`](RAPPORT_TECHNIQUE.md) |
| **Comment lancer (Docker/local, tous modes)** | [`docs/GUIDE_LANCEMENT.md`](GUIDE_LANCEMENT.md) |
| **Mettre en ligne sur un VPS (test d'équipe)** | [`docs/DEPLOIEMENT_TEST.md`](DEPLOIEMENT_TEST.md) |
| ADR individuelles | [`docs/adr/`](adr/) |
| Import de données antérieures | [`docs/migration.md`](migration.md) |

## Ce qui est fait (étapes 1 à 8, complètes)

Cœur RAG + agent LangGraph (indice 0-4, frustration, garde-fous, fallback LLM
Mistral→Ollama→Mock) + persistance PostgreSQL (RLS) + API FastAPI (SSE) +
ingestion asynchrone ARQ + frontend Streamlit + déploiement Docker Compose +
documentation complète. Détail exhaustif : `docs/RAPPORT_TECHNIQUE.md`.

**Ajouté après la clôture initiale des 8 étapes** :
- Logging JSON structuré (`agent_tuteur/observability.py`) + trace
  d'orchestration nœud-par-nœud persistée et visible dans Streamlit (page Logs).
- Détection des documents « orphelins » : un document marqué `indexed` dont les
  vecteurs ont disparu du vectorstore (ex. après un changement de
  `VECTOR_BACKEND`) est maintenant détecté (`POST /api/documents/verify-all` +
  vérification automatique au démarrage) et marqué `orphaned` plutôt que de
  rester silencieusement introuvable.

## ⚠️ Travail non commité à ce jour

```
M  agent-tuteur-api/src/agent_tuteur/agent/graph.py
M  agent-tuteur-api/src/agent_tuteur/agent/prompt.py
M  agent-tuteur-api/src/agent_tuteur/agent/state.py
M  agent-tuteur-api/src/agent_tuteur/api/routes/chat.py
M  agent-tuteur-api/src/agent_tuteur/api/routes/documents.py
```

Deux corrections liées, trouvées en testant un vrai cas d'usage (exercice
d'intégrale à plusieurs tours) plutôt qu'en lisant le code — détail complet
dans la mémoire `feedback-verify-real-infra` :

1. **L'agent RAG ignorait l'historique de conversation.** `retrieve_context`
   et `assemble_prompt` ne voyaient que le dernier message brut ; une relance
   courte de l'élève ("un autre indice ?") produisait une requête vectorielle
   sans signal mathématique, ramenant des chunks hors-sujet que le LLM
   restituait fidèlement (persona « tu t'appuies strictement sur les extraits
   fournis »). Fix : `chat.py` recharge l'historique persisté
   (`MessageRepository.list_for_conversation`) et le passe à
   `TutorAgent.prepare(conversation_history=...)` ; `graph.py` condense
   requête-courante + questions précédentes avant l'embedding
   (`_condense_retrieval_query`) ; `prompt.py` réinjecte les derniers tours
   dans le prompt final (`build_history_block`). `SessionState.recent_questions`
   est aussi rechargé depuis cet historique (la détection de frustration
   repartait de zéro à chaque requête HTTP sinon).
2. **Upload multi-fichiers cassé au 2ᵉ fichier** (`documents.py`) :
   `session.commit()` entre deux fichiers de la boucle clôt la transaction et
   efface le `set_config('app.tenant_id', ..., true)` (RLS, local à la
   transaction) → `InsufficientPrivilegeError` dès le 2ᵉ fichier. Fix :
   ré-appliquer `set_tenant_context(session, tenant_id)` après chaque commit
   de la boucle.

Les deux ont été vérifiés en conditions réelles (stack `docker-compose.dev.yml`
complète, corpus de 2 chunks — un pertinent + un leurre — indexé dans Qdrant,
scénario à 2 tours rejoué via `/api/chat`) : sans historique les deux chunks
étaient à égalité (score 0.833/0.833, tirage arbitraire) ; avec historique le
chunk pertinent remonte à 1.0 contre 0.667 pour le leurre, et la réponse LLM
reste sur le bon sujet.

3. **Système de sessions de chat** (nouveau, pas un fix) : une conversation
   n'était accessible que côté client (`st.session_state`, perdue au rechargement
   de la page), sans façon de lister/reprendre/supprimer une session passée bien
   que l'historique soit déjà persisté en base. Ajouté :
   - `conversations.title` (migration `0004_add_conversation_title`), dérivé de
     la première question (`chat.py::_make_title`, tronqué à 60 caractères).
   - `ConversationRepository.list_for_student` (tri par activité la plus
     récente, via `MAX(messages.created_at)`) et `.delete` (cascade FK).
   - Routes `GET /api/conversations?student_id=`, `GET
     /api/conversations/{id}/messages`, `DELETE /api/conversations/{id}`
     (`api/routes/conversations.py`, nouveau routeur enregistré dans `main.py`).
   - Sidebar Streamlit (`services/session.py::render_conversation_sidebar`) :
     bouton « Nouvelle conversation », liste cliquable des sessions passées
     (reprend l'historique complet), suppression par session.
   - Vérifié via l'API réelle (create → list triée → messages → delete) ;
     **le rendu du frontend Streamlit lui-même n'a PAS été vérifié dans un
     navigateur** (pas d'outil de contrôle navigateur disponible dans cette
     session) — seulement relu et vérifié syntaxiquement. À tester
     visuellement sur http://localhost:8501 avant de considérer fini.

Rien de tout ça n'est commité automatiquement (jamais sans demande explicite)
— à committer toi-même, ou demande-le en début de prochaine session.

## État de l'environnement (au moment de la pause)

- **Conteneurs Docker actifs** : stack complète `docker-compose.dev.yml`
  (préfixe `agent-tuteur-senegal-*` : postgres, redis, qdrant, api, worker,
  frontend). Démarrée pour vérifier le fix ci-dessus, laissée active à la
  demande de l'utilisateur. Volumes créés à zéro pendant cette session (corpus
  vide au départ) ; les documents de test insérés pour la vérification ont été
  supprimés après coup (`DELETE /api/documents/{id}` ×5) — le corpus est donc
  actuellement vide, à réuploader.
- Les anciens conteneurs jetables `tutor-pg`/`tutor-redis`/`qdrant` standalone
  mentionnés dans une version précédente de ce fichier ne sont plus actifs —
  cette session utilise le stack `docker compose` complet, pas le mode hybride.
- `agent-tuteur-api/.venv` non revérifié cette session (le fix a été testé via
  `/home/aimssn/nuru/rag-agent-pedagogie/.venv/bin/python -m pytest`, exécuté
  **depuis `agent-tuteur-api/`** — lancer pytest depuis la racine du repo fait
  échouer ~26 tests en cascade, config/env non trouvés depuis ce cwd).

## Reprendre rapidement

```bash
cd /home/aimssn/nuru/rag-agent-pedagogie
docker ps --format "{{.Names}}: {{.Ports}}"   # vérifier que la stack tourne encore
# sinon :
cd agent-tuteur-deploy && docker compose -f docker-compose.dev.yml up -d
```

## Pièges déjà rencontrés cette session (évite de les re-découvrir)

1. `EMBEDDING_BACKEND=bg_m3` (typo) → `ValidationError` Pydantic, app ne démarre
   pas du tout. Valeur correcte : `bge_m3`.
2. `VECTOR_BACKEND=qdrant` sans Qdrant lancé → l'API plante au démarrage (pas
   de repli gracieux, contrairement à Redis).
3. `make worker` sans Redis lancé → échec attendu (ARQ a besoin de Redis pour
   démarrer, aucun mode dégradé pour le worker lui-même).
4. Séries `"S"`/`"LS"` (au lieu de `S1`-`S5`/`L1a`-`LA` etc.) ne matchent aucun
   alias de la taxonomie — le filtrage RAG par série échoue silencieusement.
5. Changer `VECTOR_BACKEND` en cours de route (memory ↔ qdrant) rend les
   documents déjà « indexed » orphelins — c'est précisément ce que la nouvelle
   détection (`verify-all` + check au démarrage) signale désormais.
