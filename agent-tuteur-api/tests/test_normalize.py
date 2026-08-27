from agent_tuteur.ingestion.normalize import to_pivot


def test_dehyphenate_line_wrap():
    # Artefact typique d'extraction PDF : mot coupé en fin de ligne.
    assert "dérivée" in to_pivot("la déri-\nvée de la fonction")


def test_heading_gets_space_after_hashes():
    assert "## Titre" in to_pivot("##Titre\n\ncontenu")


def test_collapse_blank_lines_and_trailing_ws():
    out = to_pivot("a   \n\n\n\nb")
    assert "a\n\nb" in out
    assert "   \n" not in out


def test_crlf_normalized_and_latex_preserved():
    out = to_pivot("Formule : $x^2$\r\n\r\ndouble $$\\frac{a}{b}$$")
    assert "\r" not in out
    assert "$x^2$" in out
    assert "$$\\frac{a}{b}$$" in out


# --- Délimiteurs LaTeX (cas QA #37 et #47) -----------------------------------
# Le format pivot annoncé en tête de module est « $ … $ / $$ … $$ », mais les 12
# leçons du corpus écrivent « \( … \) » : ces extraits partaient tels quels dans
# le prompt, et le modèle recopiait la typographie qu'on lui montrait. Le rendu
# reproché par les testeurs vient donc du corpus, pas du modèle.


def test_delimiteurs_inline_ramenes_au_format_pivot():
    out = to_pivot(r"Calculer \( \int_1^2 (2x+1)\,dx \) sur l'intervalle")
    assert r"\(" not in out and r"\)" not in out
    assert r"$ \int_1^2 (2x+1)\,dx $" in out


def test_delimiteurs_bloc_ramenes_au_format_pivot():
    out = to_pivot(r"Théorème : \[ F(b)-F(a) \] pour toute primitive")
    assert r"\[" not in out and r"\]" not in out
    assert "$$ F(b)-F(a) $$" in out


def test_les_parentheses_ordinaires_ne_sont_pas_touchees():
    """Garde-fou : la transformation porte sur les délimiteurs, pas sur le texte."""
    texte = "La dérivée (au sens de Leibniz) vaut 2x [voir chapitre 4]"
    assert to_pivot(texte).strip() == texte


def test_le_contenu_mathematique_est_preserve_a_l_identique():
    out = to_pivot(r"\( \dfrac{u'v - uv'}{v^2} \)")
    assert r"\dfrac{u'v - uv'}{v^2}" in out
