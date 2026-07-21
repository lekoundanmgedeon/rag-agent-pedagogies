from agent_tuteur.agent.course_plan import (
    FIRST_INDEX,
    LAST_INDEX,
    LESSON_SECTIONS,
    advance,
    resolve_chapitre,
    resolve_goto,
    topic_terms,
)
from agent_tuteur.agent.intent import Navigation


def test_plan_has_eight_curated_sections():
    keys = [s.key for s in LESSON_SECTIONS]
    assert keys == [
        "introduction",
        "definitions",
        "theoremes",
        "methodes",
        "exemples",
        "erreurs",
        "exercices",
        "resume",
    ]


def test_start_begins_at_first_section_with_chapter():
    pos = advance(None, Navigation.START, "explique-moi les complexes", chapitre_fallback="Nombres complexes")
    assert pos.section_index == FIRST_INDEX
    assert pos.chapitre == "Nombres complexes"


def test_no_previous_state_starts_course():
    pos = advance(None, None, "explique", chapitre_fallback="Suites")
    assert pos.section_index == FIRST_INDEX


def test_next_advances_and_keeps_chapter():
    prev = {"chapitre": "Suites", "section_index": 1}
    pos = advance(prev, Navigation.NEXT, "continue", chapitre_fallback=None)
    assert pos.section_index == 2
    assert pos.chapitre == "Suites"


def test_next_is_bounded_at_last_section():
    prev = {"chapitre": "Suites", "section_index": LAST_INDEX}
    pos = advance(prev, Navigation.NEXT, "continue", chapitre_fallback=None)
    assert pos.section_index == LAST_INDEX


def test_prev_is_bounded_at_first_section():
    prev = {"chapitre": "Suites", "section_index": FIRST_INDEX}
    pos = advance(prev, Navigation.PREV, "reviens", chapitre_fallback=None)
    assert pos.section_index == FIRST_INDEX


def test_goto_jumps_to_named_section():
    prev = {"chapitre": "Suites", "section_index": 0}
    pos = advance(prev, Navigation.GOTO, "passe aux exercices", chapitre_fallback=None)
    assert pos.section.key == "exercices"


def test_goto_unresolved_keeps_current_section():
    prev = {"chapitre": "Suites", "section_index": 3}
    pos = advance(prev, Navigation.GOTO, "va voir ailleurs", chapitre_fallback=None)
    assert pos.section_index == 3


def test_follow_up_stays_on_current_section():
    prev = {"chapitre": "Suites", "section_index": 4}
    pos = advance(prev, None, "je n'ai pas compris", chapitre_fallback=None)
    assert pos.section_index == 4


def test_resolve_goto_returns_first_mentioned_in_plan_order():
    # « définitions » (index 1) précède « exercices » (index 6) dans le plan.
    assert resolve_goto("montre définitions puis exercices") == 1
    assert resolve_goto("aucune section ici") is None


# --- Liaison du chapitre à la demande de l'élève -----------------------------


def test_topic_terms_keeps_only_the_subject():
    assert topic_terms("Explique moi les nombres complexes") == ["nombres", "complexes"]
    assert topic_terms("fais-moi un cours sur les suites") == ["suites"]


def test_binding_matches_chapter_named_in_the_question():
    binding = resolve_chapitre(
        "Explique moi les nombres complexes",
        ["Suites Numeriques", "Les Nombres Complexes", "L'Arithmétique"],
    )
    # Le chapitre demandé l'emporte même s'il n'est PAS le mieux classé par le RAG.
    assert binding.chapitre == "Les Nombres Complexes"
    assert binding.confirmed is True


def test_binding_tolerates_singular_plural_mismatch():
    binding = resolve_chapitre(
        "explique-moi les dérivées", ["Fonction dérivée et équation de la tangente"]
    )
    assert binding.confirmed is True


def test_binding_refuses_to_substitute_an_unrelated_chapter():
    """Le bug d'origine : « nombres complexes » enseigné comme « Suites »."""
    binding = resolve_chapitre(
        "Explique moi les nombres complexes", ["Suites Numeriques", "Fonctions Numeriques"]
    )
    assert binding.chapitre is None
    assert binding.confirmed is False
    # Les chapitres réellement disponibles restent proposables à l'élève.
    assert binding.alternatives == ("Suites Numeriques", "Fonctions Numeriques")


def test_start_without_matching_chapter_is_unconfirmed():
    binding = resolve_chapitre("explique-moi la photosynthèse", ["Suites Numeriques"])
    pos = advance(None, Navigation.START, "explique-moi la photosynthèse", binding=binding)
    assert pos.chapitre is None
    assert pos.chapitre_confirmed is False
    assert pos.alternatives == ("Suites Numeriques",)


def test_explicit_curriculum_chapter_wins_over_failed_binding():
    """Un chapitre choisi explicitement par l'élève n'a pas à être redeviné."""
    binding = resolve_chapitre("commence", ["Suites Numeriques"])
    pos = advance(None, Navigation.START, "commence", chapitre_fallback="Calcul Integral", binding=binding)
    assert pos.chapitre == "Calcul Integral"
    assert pos.chapitre_confirmed is True


def test_unconfirmed_chapter_stays_unconfirmed_across_navigation():
    prev = {"chapitre": None, "section_index": 0}
    pos = advance(prev, Navigation.NEXT, "continue")
    assert pos.chapitre_confirmed is False


def test_navigation_never_rebinds_the_chapter():
    prev = {"chapitre": "Suites Numeriques", "section_index": 0}
    # Un mot de sujet dans une relance ne doit pas faire dériver le cours.
    pos = advance(prev, Navigation.NEXT, "continue avec les nombres complexes")
    assert pos.chapitre == "Suites Numeriques"
