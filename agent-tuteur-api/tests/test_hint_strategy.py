from agent_tuteur.agent.hint_strategy import diagnose_hint_level, wants_direct_correction


def test_base_level_is_one():
    d = diagnose_hint_level("comment résoudre cette équation du second degré ?")
    assert d.level == 1
    assert d.label == "Rappel de notion"


def test_short_question_drops_to_zero():
    d = diagnose_hint_level("et après ?")
    assert d.level == 0


def test_repetition_escalates_by_one():
    d = diagnose_hint_level("comment dériver cette fonction rationnelle ?", repetitions=2)
    assert d.level == 2


def test_frustration_escalates_by_one():
    d = diagnose_hint_level("je ne comprends toujours pas cette méthode", frustration_score=0.5)
    assert d.level == 2


def test_escalations_are_cumulative_and_bounded():
    d = diagnose_hint_level(
        "je n'y arrive vraiment pas du tout", frustration_score=0.9, repetitions=3
    )
    # base 1 + rep + frustration = 3, borné [0,4].
    assert d.level == 3


def test_explicit_correction_jumps_to_four():
    assert wants_direct_correction("donne-moi la réponse")
    d = diagnose_hint_level("donne-moi la réponse", frustration_score=0.0)
    assert d.level == 4
    assert d.reason == "demande explicite de correction"


def test_level_never_exceeds_four():
    d = diagnose_hint_level(
        "je bloque complètement là-dessus depuis longtemps",
        frustration_score=1.0,
        repetitions=10,
    )
    assert d.level <= 4
