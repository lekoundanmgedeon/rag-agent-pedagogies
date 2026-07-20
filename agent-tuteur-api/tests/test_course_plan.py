from agent_tuteur.agent.course_plan import (
    FIRST_INDEX,
    LAST_INDEX,
    LESSON_SECTIONS,
    advance,
    resolve_goto,
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
