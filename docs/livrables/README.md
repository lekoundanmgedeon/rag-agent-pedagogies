# Livrables Word — réunion technique

Fichiers `.docx` **générés** depuis les sources Markdown de `docs/`.
La source de vérité reste le Markdown : après toute modification, régénérer.

```bash
# depuis la racine du dépôt
.venv/bin/python docs/livrables/md2docx.py docs docs/livrables
```

| Fichier | Usage en réunion |
|---|---|
| `SYNTHESE_REUNION_TECHNIQUE.docx` | À distribuer autour de la table — support de discussion |
| `COMPARATIF_ARCHITECTURES.docx` | Document de référence, à consulter sur un point précis |
| `ARCHITECTURE_CIBLE.docx` | Annexe développeurs, pour l'après-réunion |

**Sommaire** : dans les deux documents longs, faire un clic droit sur le cadre
« Sommaire » → *Mettre à jour les champs* (Word ne calcule une table des
matières qu'à la demande).

**Diagrammes** : les schémas Mermaid d'`ARCHITECTURE_CIBLE` apparaissent en code
source. Pour le rendu graphique, coller le bloc sur <https://mermaid.live> ou
consulter la version Markdown.
