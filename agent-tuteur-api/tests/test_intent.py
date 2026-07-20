from agent_tuteur.agent.intent import Intent, Navigation, classify_intent


def test_default_is_exercise():
    d = classify_intent("comment résoudre cette équation du second degré ?")
    assert d.intent == Intent.EXERCICE
    assert d.navigation is None


def test_explicit_course_request_starts_course():
    for q in (
        "explique-moi les nombres complexes",
        "fais-moi un cours sur les suites",
        "je veux apprendre les probabilités",
        "c'est quoi une intégrale ?",
        "présente le chapitre sur l'arithmétique",
    ):
        d = classify_intent(q)
        assert d.intent == Intent.COURS, q
        assert d.navigation == Navigation.START, q


def test_navigation_only_ignored_outside_course():
    # « continue » n'a aucun sens hors d'un cours : on retombe sur l'exercice.
    d = classify_intent("continue", in_course=False)
    assert d.intent == Intent.EXERCICE


def test_navigation_next_inside_course():
    d = classify_intent("continue", in_course=True)
    assert d.intent == Intent.COURS
    assert d.navigation == Navigation.NEXT


def test_navigation_goto_inside_course():
    d = classify_intent("passe aux exercices", in_course=True)
    assert d.intent == Intent.COURS
    assert d.navigation == Navigation.GOTO


def test_section_mention_inside_course_is_goto():
    d = classify_intent("et les définitions ?", in_course=True)
    assert d.intent == Intent.COURS
    assert d.navigation == Navigation.GOTO


def test_follow_up_stays_in_course_without_nav():
    # Une sous-question dans le cours reste en mode cours, section courante.
    d = classify_intent("je n'ai pas compris le module", in_course=True)
    assert d.intent == Intent.COURS
    assert d.navigation is None


def test_explicit_course_start_overrides_in_course():
    # Ouvrir un nouveau chapitre en plein cours redémarre bien un cours.
    d = classify_intent("explique-moi maintenant les statistiques", in_course=True)
    assert d.navigation == Navigation.START


def test_solve_request_breaks_out_of_course():
    # Piège du « mode collant » : une demande de résolution en plein cours doit
    # repartir sur le pipeline exercice (trouvé en vérif de flux réel).
    for q in ("calcule la dérivée de x^3 - 3x", "résous cette équation", "corrige mon exercice"):
        d = classify_intent(q, in_course=True)
        assert d.intent == Intent.EXERCICE, q


def test_difficulty_expression_does_not_break_out():
    # Une expression de difficulté n'est PAS une demande de résolution : on reste.
    for q in ("je ne trouve pas", "je n'ai pas compris la démonstration"):
        d = classify_intent(q, in_course=True)
        assert d.intent == Intent.COURS, q
