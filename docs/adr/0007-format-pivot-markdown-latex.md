# ADR 0007 — Format pivot Markdown + LaTeX partagé corpus/OCR

## Contexte

Le contenu curriculaire provient de sources hétérogènes (Markdown rédigé à la
main, PDF/DOCX extraits automatiquement, et à terme une sortie OCR pour les
documents scannés). Les questions des élèves sont, elles, du texte libre. Si
le contenu indexé et les questions ne vivent pas dans le même espace
typographique, l'embedding diverge silencieusement entre les deux — dégradation
du retrieval difficile à diagnostiquer.

## Décision

Un **format pivot unique** — Markdown + LaTeX inline (`$...$`, `$$...$$`) —
que **toute** extraction (PDF, DOCX, TXT, MD, et la future sortie OCR) traverse
via le même normaliseur (`ingestion/normalize.py::to_pivot`) avant chunking.

## Justification

- Markdown est lisible tel quel par un humain (corpus d'exemple écrit à la
  main) et suffisamment structuré pour porter les marqueurs de chunking
  (`## `, `### Exercice`).
- LaTeX inline est la notation naturelle pour les formules mathématiques et
  physiques (cœur du corpus scolaire sénégalais), et cohérente avec ce qu'un
  élève taperait dans sa question (`$x^2$`).
- Un normaliseur unique garantit qu'un PDF extrait avec des artefacts
  (mots coupés en fin de ligne, titres sans espace après `#`) converge vers la
  même forme que le Markdown écrit à la main — pas de double standard à
  maintenir.

## Conséquences

- Le normaliseur doit rester **conservateur** (pas de réécriture sémantique) :
  il corrige des artefacts d'extraction, il ne reformule pas le contenu.
- La sortie OCR (non implémentée dans le périmètre actuel) devra produire du
  Markdown+LaTeX directement ou passer par un post-traitement vers ce format
  avant d'entrer dans le pipeline d'ingestion — condition non négociable pour
  ne pas réintroduire la divergence que ce choix vise à éviter.
