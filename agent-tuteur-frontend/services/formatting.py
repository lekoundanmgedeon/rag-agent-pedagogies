"""Normalisation des délimiteurs LaTeX avant rendu Markdown Streamlit.

Le persona demande au LLM le style ``$...$``/``$$...$$`` (seul interprété par
le rendu Markdown de Streamlit), mais certains fournisseurs (Mistral en tête)
répondent parfois avec le style MathJax/ChatGPT ``\\(...\\)``/``\\[...\\]``.
Le CommonMark de Streamlit traite alors ces antislashs comme de simples
échappements de ponctuation et les supprime (``\\(`` → ``(``, ``\\,`` → ``,``),
laissant du LaTeX brut illisible à l'écran. On convertit donc systématiquement
avant affichage, quel que soit le respect de la consigne par le LLM.
"""

from __future__ import annotations

import re

_DISPLAY_MATH = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
_INLINE_MATH = re.compile(r"\\\((.*?)\\\)", re.DOTALL)


def normalize_latex_delimiters(text: str) -> str:
    text = _DISPLAY_MATH.sub(lambda m: f"$${m.group(1)}$$", text)
    text = _INLINE_MATH.sub(lambda m: f"${m.group(1)}$", text)
    return text
