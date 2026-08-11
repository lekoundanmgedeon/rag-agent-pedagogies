import pytest

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


# --- Intention méta (cas QA #2, #3, #4) --------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Quel est mon programme de cette année",
        "Quels sont les grands chapitres au programme de mathématiques en Terminale S ?",
        "quelles leçons sont disponibles ?",
        "sur quels chapitres peux-tu m'aider ?",
        "qu'est-ce que tu sais faire ?",
        "comment tu fonctionnes ?",
    ],
)
def test_meta_sans_ambiguite_reconnu_partout(question):
    assert classify_intent(question).intent == Intent.META, question
    # Même en plein cours : la question ne porte pas sur la notion enseignée.
    assert classify_intent(question, in_course=True).intent == Intent.META, question


@pytest.mark.parametrize(
    "question",
    [
        "Donne moi des astuces pour m'améliorer en maths ?",
        "des conseils pour progresser en maths",
        "comment réviser efficacement pour le bac ?",
    ],
)
def test_meta_de_methode_reconnu_hors_cours(question):
    assert classify_intent(question).intent == Intent.META, question


def test_les_astuces_restent_une_section_pendant_un_cours():
    """Frontière délicate : « astuces » nomme une section du plan de cours.

    Sans cette distinction, le routeur méta volerait la navigation intra-cours
    déjà couverte par test_section_mention_inside_course_is_goto.
    """
    d = classify_intent("donne-moi les astuces", in_course=True)
    assert d.intent == Intent.COURS
    assert d.navigation == Navigation.GOTO


@pytest.mark.parametrize(
    "question",
    [
        # Questions de contenu : le mot « chapitre » ne suffit pas à faire méta.
        "présente le chapitre sur les nombres complexes",
        "Quelle est la différence entre une suite arithmétique et une suite géométrique ?",
        "Comment dériver un quotient de fonctions ?",
        "Comment puis-je tricher à mon examen de maths ?",
        "Fais-moi un cours sur les suites numériques",
    ],
)
def test_les_questions_de_contenu_ne_deviennent_pas_meta(question):
    assert classify_intent(question).intent != Intent.META, question
