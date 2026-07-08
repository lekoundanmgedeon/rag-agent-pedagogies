from agent_tuteur.agent.frustration import (
    SessionState,
    count_markers,
    count_repetitions,
    detect_frustration,
)


def test_repetition_detected_above_threshold():
    recent = ["comment calculer la dérivée d'un quotient de fonctions"]
    # Question quasi identique -> Jaccard >= 0.8.
    assert count_repetitions("comment calculer la dérivée d'un quotient de fonctions ?", recent) == 1


def test_distinct_questions_are_not_repetitions():
    recent = ["parle-moi des suites géométriques"]
    assert count_repetitions("comment tracer une parabole", recent) == 0


def test_markers_counted():
    assert count_markers("je comprends pas, donne-moi la réponse") == 2
    assert count_markers("merci beaucoup pour l'explication") == 0


def test_score_formula():
    session = SessionState()
    session.recent_questions = ["même question exacte ici", "même question exacte ici"]
    signal = detect_frustration("même question exacte ici", session)
    # 2 répétitions (0.3*2=0.6) ; pas de marqueur -> min(1, 0.6) = 0.6.
    assert signal.repetitions == 2
    assert signal.score == 0.6


def test_score_capped_at_one():
    session = SessionState()
    # Répétitions (0.3*5) + marqueurs (0.4*2) = 2.3, borné à 1.0.
    session.recent_questions = ["je bloque là je comprends pas"] * 5
    signal = detect_frustration("je bloque là je comprends pas", session)
    assert signal.score == 1.0


def test_session_is_ephemeral_window():
    session = SessionState()
    for i in range(20):
        session.add(f"question {i}")
    # La fenêtre glissante borne la taille (non persistée indéfiniment).
    assert len(session.recent_questions) <= 10
