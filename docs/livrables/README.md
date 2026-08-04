# Livrables Word — réunion technique

Fichiers `.docx` **générés** depuis les sources Markdown de `docs/`.
La source de vérité reste le Markdown : après toute modification, régénérer.

```bash
# depuis la racine du dépôt
.venv/bin/python docs/livrables/md2docx.py docs docs/livrables
```

| Fichier | Usage en réunion |
|---|---|
| `RAPPORT_FUSION.docx` | **Le document de la réunion** — ce qui a été décidé, pourquoi, et les 7 points à trancher |
| `SYNTHESE_REUNION_TECHNIQUE.docx` | Le plan d'origine, pour comparer avec ce qui a été fait |
| `COMPARATIF_ARCHITECTURES.docx` | Document de référence, à consulter sur un point précis |
| `ARCHITECTURE_CIBLE.docx` | Annexe développeurs, pour l'après-réunion |

**Sommaire** : dans les deux documents longs, faire un clic droit sur le cadre
« Sommaire » → *Mettre à jour les champs* (Word ne calcule une table des
matières qu'à la demande).

**Ordre de lecture** : `RAPPORT_FUSION` suffit pour la réunion. Les trois
autres sont les documents d'origine (le plan et son analyse), à consulter si une
décision est contestée.

**Diagrammes** : les schémas Mermaid d'`ARCHITECTURE_CIBLE` apparaissent en code
source. Pour le rendu graphique, coller le bloc sur <https://mermaid.live> ou
consulter la version Markdown.
