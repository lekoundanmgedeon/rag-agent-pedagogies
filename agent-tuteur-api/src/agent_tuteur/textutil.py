"""Utilitaires texte partagés (tokenisation, accents, similarité lexicale).

Regroupés ici pour garantir que l'*embedder* léger, le retriever et la détection
de frustration parlent le même langage : mêmes tokens, même normalisation. Une
divergence à ce niveau désaligne silencieusement l'espace d'embedding.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def strip_accents(text: str) -> str:
    """Retire les diacritiques : « dérivée » et « derivee » deviennent égaux."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    """Tokens alphanumériques minusculés, accents retirés.

    Volontairement simple et déterministe : la ponctuation LaTeX/Markdown est
    ignorée, seuls les mots et nombres subsistent.
    """
    return _TOKEN_RE.findall(strip_accents(text.lower()))


def char_ngrams(token: str, n: int = 3) -> list[str]:
    """N-grammes de caractères d'un token, bornés par ``^``/``$``.

    Apportent un signal sub-lexical (fautes de frappe, variantes morphologiques)
    à l'embedding dense par hachage.
    """
    padded = f"^{token}$"
    if len(padded) <= n:
        return [padded]
    return [padded[i : i + n] for i in range(len(padded) - n + 1)]


def stable_hash(text: str) -> int:
    """Hash entier déterministe (indépendant du PYTHONHASHSEED)."""
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def jaccard(a: str, b: str) -> float:
    """Similarité de Jaccard entre deux textes (ensembles de tokens)."""
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
