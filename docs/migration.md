# Migration — import de données antérieures (best-effort)

Ce projet a été construit *from scratch* (aucun code ni schéma antérieur
disponible dans le périmètre de cette session). Ce document décrit la
**méthode** à suivre pour importer des données d'une plateforme existante
(par exemple une précédente implémentation de la référentiel), plutôt qu'un
script concret — aucun accès à un schéma source n'a été fourni.

## 1. Contenu curriculaire (corpus)

Si le contenu existant est dans un format hétérogène (HTML, texte brut,
export d'une autre plateforme) :

1. **Convertir vers le format pivot** (Markdown + LaTeX inline, cf. ADR 0007)
   *avant* tout import — ne jamais indexer directement un format tiers, sous
   peine de désaligner l'espace d'embedding entre contenu et questions élève
   (c'est précisément le problème que le format pivot évite).
2. **Structurer avec les marqueurs de chunking** (`## ` pour chapitre/
   compétence, `### Exercice` pour un exercice) si le contenu source ne les a
   pas déjà — un export automatique tombera sinon sur l'heuristique de repli
   (`ingestion/chunking.py`), moins fiable qu'un marquage explicite.
3. **Importer via `POST /api/documents`** avec les champs de métadonnées
   curriculaires (`niveau`, `classe`, `serie`, `discipline`, `chapitre`,
   `competence`, `examen_associe`) renseignés depuis le système source — ne
   pas dupliquer un schéma de métadonnées parallèle : `CurriculumMetadata`
   fait foi.
4. Pour un volume important, scripter l'appel HTTP en lot plutôt qu'un import
   direct dans Qdrant : cela garantit que chaque document passe par le même
   pipeline (normalize→chunk→annotate→embed) que l'ingestion standard, et que
   `documents.status` reste la source de vérité de ce qui a été indexé.

## 2. Progression élève / historique

Si une plateforme antérieure a des données de progression élève à conserver :

1. Vérifier la correspondance des champs avec `progress`
   (`student_id, tenant_id, competence, hint_level, question, created_at`) —
   le `hint_level` (0-4) n'a de sens que s'il suit la même échelle que
   `agent/hint_strategy.py` ; à défaut, ne pas forcer une correspondance
   approximative (mieux vaut ne pas importer un niveau d'indice non comparable
   que d'en fausser les statistiques de difficultés récurrentes).
2. Insérer directement en base via un script utilisant
   `persistence.repositories.ProgressRepository.record()` (respecte le même
   chemin que l'agent, garantit la cohérence du format) plutôt qu'un `INSERT`
   SQL brut qui contournerait toute validation applicative.
3. **Ne pas importer l'état de session/frustration** : c'est explicitement
   éphémère et non persisté par conception (cf. ADR sur la détection de
   frustration) — seul le résultat notable (compétence, niveau d'indice
   atteint) a un sens à long terme.

## 3. Comptes / tenants

Attribuer un `tenant_id` stable à chaque école/institution important des
données, cohérent avec celui qui sera utilisé en production (en-tête
`X-Tenant-Id`) — un tenant mal aligné entre l'import et l'usage réel rendrait
les données importées invisibles (RLS + filtrage applicatif les isoleraient
silencieusement dans le mauvais tenant).

## 4. Ce qui n'est délibérément pas couvert

- Aucun connecteur concret n'est fourni ici (pas de schéma source connu à ce
  jour) — ce document sert de guide de méthode, pas de script clé en main.
- Les documents originaux (fichiers PDF/DOCX sources) ne sont pas conservés
  par la plateforme (pas de stockage d'objets dans la stack verrouillée, cf.
  `docs/api.md#post-apidocumentsdocument_idreindex`) : prévoir leur archivage
  côté système source si une ré-indexation future est anticipée.
