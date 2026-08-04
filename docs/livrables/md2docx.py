"""Conversion Markdown -> Word (.docx) pour les livrables de la réunion technique.

Couvre le sous-ensemble Markdown réellement utilisé dans docs/ :
titres, tableaux GFM, blocs de code clôturés, citations, listes, règles
horizontales, et le formatage inline (gras, italique, code, liens).

pandoc n'étant pas installé sur cette machine, la conversion est faite avec
python-docx.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

MONO = "Consolas"
BODY = "Calibri"

CODE_BG = "F4F4F5"
QUOTE_BG = "FFF7E6"
CODE_COLOR = RGBColor(0x0B, 0x3D, 0x91)

# Ordre important : le code inline est capturé en premier pour que son contenu
# ne soit pas réinterprété (un `**` dans du code doit rester littéral).
INLINE_RE = re.compile(
    r"(`[^`]+`"
    r"|\*\*[^*]+?\*\*"
    r"|\*[^*\s][^*]*?\*"
    r"|\[[^\]]+\]\([^)]*\))"
)


# --------------------------------------------------------------------- helpers


def _shade(paragraph, fill: str) -> None:
    """Applique un fond de couleur à un paragraphe."""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    paragraph._p.get_or_add_pPr().append(shd)


def _left_border(paragraph, color: str = "D9822B") -> None:
    """Barre verticale à gauche (citations)."""
    pbdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), color)
    pbdr.append(left)
    paragraph._p.get_or_add_pPr().append(pbdr)


def _page_number_footer(section) -> None:
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for instr in ("begin", "instrText", "end"):
        el = OxmlElement(f"w:fld{instr.capitalize()}" if instr != "instrText" else "w:instrText")
        if instr == "instrText":
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        else:
            el.set(qn("w:fldCharType"), instr)
        run._r.append(el)
    p.runs[0].font.size = Pt(8)
    p.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)


def _toc(document) -> None:
    """Insère un champ table des matières (à mettre à jour à l'ouverture)."""
    p = document.add_paragraph()
    run = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-3" \h \z \u'
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Sommaire — clic droit sur ce cadre puis « Mettre à jour les champs »."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, placeholder, end):
        run._r.append(el)


#: Caractères qu'un auteur peut échapper en Markdown pour les afficher tels
#: quels (``\*`` pour un astérisque littéral, typique d'un appel de note).
#: Sans ce traitement, la barre oblique se retrouvait visible dans le Word.
_ECHAPPEMENT = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~])")


def _desechapper(texte: str) -> str:
    """Retire les barres obliques d'échappement Markdown."""
    return _ECHAPPEMENT.sub(r"\1", texte)


def _add_inline(paragraph, text: str, *, bold=False, italic=False, size=None, color=None):
    """Écrit du texte en appliquant le formatage inline Markdown."""
    for token in INLINE_RE.split(text):
        if not token:
            continue
        run = None
        if token.startswith("`") and token.endswith("`") and len(token) > 1:
            run = paragraph.add_run(token[1:-1])
            run.font.name = MONO
            run.font.size = Pt(9)
            run.font.color.rgb = CODE_COLOR
        elif token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        else:
            link = re.fullmatch(r"\[([^\]]+)\]\(([^)]*)\)", token)
            if link:
                label = link.group(1).strip("`")
                run = paragraph.add_run(label)
                run.font.color.rgb = RGBColor(0x1A, 0x5F, 0xB4)
                run.underline = True
            else:
                run = paragraph.add_run(_desechapper(token))
        if run is not None:
            if bold:
                run.bold = True
            if italic:
                run.italic = True
            if size:
                run.font.size = Pt(size)
            if color:
                run.font.color.rgb = color
    return paragraph


# ---------------------------------------------------------------- block parsing


def _is_table_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?[\s:\-\|]+\|[\s:\-\|]*", line)) and "-" in line


def _split_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def convert(md_path: Path, docx_path: Path, *, with_toc: bool = False) -> None:
    lines = md_path.read_text(encoding="utf-8").split("\n")

    document = Document()

    style = document.styles["Normal"]
    style.font.name = BODY
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15
    # Police de repli pour les caractères non latins (flèches, emoji, encadrés).
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY)

    for section in document.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
        _page_number_footer(section)

    seen_title = False
    first_h1 = True
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        line = raw.rstrip()

        # --- bloc de code clôturé ---
        fence = re.match(r"^\s*```(\w*)\s*$", line)
        if fence:
            lang = fence.group(1)
            i += 1
            body: list[str] = []
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                body.append(lines[i])
                i += 1
            i += 1

            if lang == "mermaid":
                note = document.add_paragraph()
                r = note.add_run(
                    "Diagramme (source Mermaid). Rendu graphique : version Markdown "
                    "du document, ou copier-coller sur mermaid.live"
                )
                r.italic = True
                r.font.size = Pt(8.5)
                r.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
                note.paragraph_format.space_after = Pt(2)

            for text in body:
                p = document.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.left_indent = Cm(0.4)
                p.paragraph_format.line_spacing = 1.0
                run = p.add_run(text if text.strip() else "\u00a0")
                run.font.name = MONO
                run.font.size = Pt(8.5)
                _shade(p, CODE_BG)
            document.add_paragraph().paragraph_format.space_after = Pt(4)
            continue

        # --- tableau ---
        if line.startswith("|") and i + 1 < n and _is_table_sep(lines[i + 1]):
            header = _split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1

            ncols = len(header)
            table = document.add_table(rows=1, cols=ncols)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            for idx, cell_text in enumerate(header):
                cell = table.rows[0].cells[idx]
                cell.text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.space_before = Pt(2)
                _add_inline(p, cell_text, bold=True, size=9)
                _shade(p, "E8EDF3")

            for row in rows:
                cells = table.add_row().cells
                for idx in range(ncols):
                    value = row[idx] if idx < len(row) else ""
                    cells[idx].text = ""
                    p = cells[idx].paragraphs[0]
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                    _add_inline(p, value, size=9)

            document.add_paragraph().paragraph_format.space_after = Pt(4)
            continue

        # --- titres ---
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2).strip()
            if level == 1 and not seen_title:
                p = document.add_paragraph(style="Title")
                _add_inline(p, text)
                seen_title = True
            else:
                word_level = max(1, level - 1)
                if word_level == 1 and not first_h1:
                    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                if word_level == 1:
                    first_h1 = False
                p = document.add_paragraph(style=f"Heading {min(word_level, 4)}")
                _add_inline(p, text)
            i += 1
            continue

        # --- règle horizontale ---
        if re.fullmatch(r"\s*(-{3,}|\*{3,}|_{3,})\s*", line):
            p = document.add_paragraph()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "CCCCCC")
            pbdr.append(bottom)
            p._p.get_or_add_pPr().append(pbdr)
            p.paragraph_format.space_after = Pt(8)
            i += 1
            continue

        # --- citation ---
        if line.lstrip().startswith(">"):
            buf: list[str] = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            p = document.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.space_before = Pt(4)
            _add_inline(p, " ".join(x.strip() for x in buf if x.strip()), italic=False)
            _shade(p, QUOTE_BG)
            _left_border(p)
            continue

        # --- listes ---
        bullet = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        number = re.match(r"^(\s*)(\d+)[.)]\s+(.*)$", line)
        if bullet or number:
            indent = len((bullet or number).group(1))
            text = bullet.group(2) if bullet else number.group(3)
            style_name = "List Bullet" if bullet else "List Number"
            if indent >= 2:
                style_name += " 2"
            try:
                p = document.add_paragraph(style=style_name)
            except KeyError:
                p = document.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            _add_inline(p, text)
            i += 1
            continue

        # --- paragraphe ---
        if not line.strip():
            i += 1
            continue

        start = i
        buf = []
        while i < n and lines[i].strip() and not re.match(
            r"^(#{1,6}\s|\s*```|\||\s*[-*]\s|\s*\d+[.)]\s|\s*>)", lines[i]
        ) and not re.fullmatch(r"\s*(-{3,})\s*", lines[i]):
            buf.append(lines[i].strip())
            i += 1

        if not buf:
            # La ligne ouvre un bloc qu'aucune branche n'a su consommer (ex. une
            # ligne « | … » sans séparateur de tableau). On l'écrit telle quelle
            # et on avance : sans ce garde-fou, `i` ne progresse jamais.
            p = document.add_paragraph()
            _add_inline(p, lines[i].strip())
            i += 1
            continue

        p = document.add_paragraph()
        _add_inline(p, " ".join(buf))
        assert i > start, "progression du curseur non garantie"

    # Sommaire inséré juste après le titre, pour les documents longs.
    if with_toc:
        body = document.element.body
        _toc(document)
        # Le paragraphe du champ TOC est celui qu'on vient d'ajouter. Surtout pas
        # `body[-1]` : le dernier enfant du corps est le `sectPr` (propriétés de
        # section), qui DOIT rester en dernière position — le déplacer produit un
        # document OOXML invalide que Word propose de « réparer ».
        toc_p = document.paragraphs[-1]._p
        toc_p.getparent().remove(toc_p)

        anchor = next(
            (idx for idx, child in enumerate(body) if child.tag.endswith("}p")), 0
        )
        body.insert(anchor + 1, toc_p)

        tags = [c.tag.split("}")[-1] for c in body]
        assert tags[-1] == "sectPr", f"sectPr doit clore le corps, trouvé : {tags[-1]}"

    document.save(docx_path)
    print(f"✓ {docx_path.name}")


#: Documents convertis, dans l'ordre d'importance pour la réunion.
#: Le chemin source est relatif à la **racine du dépôt** : tous les documents ne
#: vivent pas dans `docs/` (le journal de fusion est à la racine, à côté du
#: README, parce qu'il s'adresse à toute l'équipe et pas seulement aux
#: développeurs). ``toc`` = insérer un sommaire, utile au-delà de ~10 sections.
DOCUMENTS: tuple[tuple[str, bool], ...] = (
    ("docs/RAPPORT_FUSION", True),
    ("JOURNAL_FUSION", True),
    ("docs/COMPARATIF_ARCHITECTURES", True),
    ("docs/SYNTHESE_REUNION_TECHNIQUE", False),
    ("docs/ARCHITECTURE_CIBLE", True),
)


if __name__ == "__main__":
    racine = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for chemin, toc in DOCUMENTS:
        source = racine / f"{chemin}.md"
        convert(source, out / f"{source.stem}.docx", with_toc=toc)
