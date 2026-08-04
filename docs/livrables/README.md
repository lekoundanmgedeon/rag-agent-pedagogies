# Livrables Word — réunion technique

Fichiers `.docx` **générés** depuis les sources Markdown de `docs/`.
La source de vérité reste le Markdown : après toute modification, régénérer.

```bash
# depuis la racine du dépôt
.venv/bin/python docs/livrables/md2docx.py . docs/livrables
```

| Fichier | Usage en réunion |
|---|---|
| `RAPPORT_FUSION.docx` | **Le document de la réunion** — ce qui a été décidé, pourquoi, et les 7 points à trancher |
| `JOURNAL_FUSION.docx` | Le détail module par module — à ouvrir si une décision du rapport est contestée |
| `SYNTHESE_REUNION_TECHNIQUE.docx` | Le plan d'origine, pour comparer avec ce qui a été fait |
| `COMPARATIF_ARCHITECTURES.docx` | Document de référence, à consulter sur un point précis |
| `ARCHITECTURE_CIBLE.docx` | Annexe développeurs, pour l'après-réunion |

**Sommaire** : dans les documents longs, faire un clic droit sur le cadre
« Sommaire » → *Mettre à jour les champs* (Word ne calcule une table des
matières qu'à la demande).

**Ordre de lecture** : `RAPPORT_FUSION` suffit pour la réunion ; `JOURNAL_FUSION`
donne le détail et les mesures derrière chaque choix. Les trois autres sont les
documents d'origine (le plan et son analyse).

**Le premier argument est la racine du dépôt** (et non `docs/`) : tous les
documents n'y vivent pas — le journal de fusion est à la racine, à côté du
README, parce qu'il s'adresse à toute l'équipe.

**Diagrammes** : les schémas Mermaid d'`ARCHITECTURE_CIBLE` apparaissent en code
source. Pour le rendu graphique, coller le bloc sur <https://mermaid.live> ou
consulter la version Markdown.
