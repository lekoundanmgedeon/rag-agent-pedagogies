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
