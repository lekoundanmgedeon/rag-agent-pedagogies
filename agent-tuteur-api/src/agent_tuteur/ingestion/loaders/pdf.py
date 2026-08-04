"""Extraction du texte d'un PDF — PyMuPDF en tête, ``pypdf`` en repli.

Pourquoi ce changement ? ``pypdf`` (utilisé jusqu'ici) restitue mal les
documents mathématiques : les fractions, indices et exposants sont aplatis ou
perdus, et l'ordre de lecture des colonnes est souvent faux. PyMuPDF respecte
la mise en page et conserve les symboles. Le corpus visé étant à 100 % des
mathématiques du secondaire, c'est un prérequis, pas un confort.

``pypdf`` **reste** présent comme repli : PyMuPDF est un extra optionnel
(``pip install 'agent-tuteur-api[parsing]'``) et l'ingestion ne doit jamais
échouer parce qu'une dépendance facultative manque — c'est la même doctrine de
repli gracieux que pour les embeddings et le vectorstore.

Porté de ``backend/app/rag/document_parser/pymupdf_adapter.py`` (NURU), avec
deux adaptations :

- **travail sur des octets, pas sur un chemin** : l'API reçoit les documents
  par téléversement, ils n'existent pas toujours sur le disque ;
- **pas d'exception nue** : un échec PyMuPDF bascule sur ``pypdf`` au lieu de
  faire remonter une ``Exception`` générique.
"""

from __future__ import annotations

import io
import logging

from agent_tuteur.ingestion.loaders.cleaners import clean_text
from agent_tuteur.observability import get_logger, log_event

_logger = get_logger("agent_tuteur.ingestion.loaders.pdf")

#: Séparateur inséré entre deux pages. Il matérialise la frontière de page dans
#: le texte pivot, ce qui aide le découpage structurel à ne pas coller la fin
#: d'un exercice au début du suivant.
PAGE_SEPARATOR = "\n\n--- Page {n} ---\n\n"


def extract_with_pymupdf(data: bytes) -> str:
    """Extrait le texte avec PyMuPDF. Lève ``ImportError`` s'il est absent."""
    import fitz  # PyMuPDF ; import tardif, la dépendance est optionnelle

    parts: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as document:
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text()
            if page_text.strip():
                parts.append(PAGE_SEPARATOR.format(n=page_number))
                parts.append(page_text)
    return clean_text("".join(parts))


def extract_with_pypdf(data: bytes) -> str:
    """Extraction de repli, sans dépendance optionnelle."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    raw = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return clean_text(raw)


def extract_pdf(data: bytes) -> str:
    """Extrait le texte d'un PDF, avec repli automatique.

    L'ordre est fixe et non configurable : il n'existe aucun cas où ``pypdf``
    donnerait un meilleur résultat que PyMuPDF sur ce corpus. Le repli sert
    uniquement de filet quand PyMuPDF est absent ou échoue sur un fichier.
    """
    try:
        return extract_with_pymupdf(data)
    except ImportError:
        log_event(_logger, "loaders:pdf_fallback", log_level=logging.WARNING,
                  reason="pymupdf_absent")
    except Exception as exc:  # fichier corrompu, chiffré, format exotique…
        log_event(_logger, "loaders:pdf_fallback", log_level=logging.WARNING,
                  reason="pymupdf_failed", error=str(exc))
    return extract_with_pypdf(data)
