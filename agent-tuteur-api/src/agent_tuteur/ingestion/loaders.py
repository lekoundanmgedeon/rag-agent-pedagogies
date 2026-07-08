"""Extraction de texte brut depuis PDF / DOCX / TXT / MD.

Chaque format produit du texte *brut* qui sera ensuite passé par le **même**
normaliseur (format pivot) que le reste — c'est la garantie de cohérence de
l'espace d'embedding entre contenu curriculaire et questions élève.
"""

from __future__ import annotations

import io
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def detect_doc_type(filename: str) -> str:
    """Type logique d'un document d'après son extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in {".md", ".markdown"}:
        return "markdown"
    if ext == ".txt":
        return "txt"
    raise ValueError(f"Extension non supportée : {ext!r} ({filename})")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document as DocxDocument

    document = DocxDocument(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Retourne ``(texte_brut, doc_type)`` pour un fichier en mémoire."""
    doc_type = detect_doc_type(filename)
    if doc_type == "pdf":
        return _extract_pdf(data), doc_type
    if doc_type == "docx":
        return _extract_docx(data), doc_type
    # txt / markdown : lecture directe (UTF-8, tolérante).
    return data.decode("utf-8", errors="replace"), doc_type


def load_file(path: str | Path) -> tuple[str, str]:
    """Charge un fichier du disque -> ``(texte_brut, doc_type)``."""
    p = Path(path)
    return extract_text(p.name, p.read_bytes())
