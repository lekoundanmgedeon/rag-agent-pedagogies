"""Détection d'intention — aiguille un tour vers le pipeline **exercice** ou **cours**.

Deux comportements coexistent :

* ``EXERCICE`` (défaut) — posture socratique à indices gradués (cf.
  ``hint_strategy.py``) : l'agent *retient* volontairement le contenu.
* ``COURS`` — posture didactique : l'agent *expose* un chapitre, section par
  section (cf. ``course_plan.py``).

La détection est **heuristique regex-first**, dans l'esprit de ``frustration.py``
et ``hint_strategy.py`` : rapide, déterministe, sans appel LLM. Le principe de
sûreté est que **le défaut reste ``EXERCICE``** — en cas d'ambiguïté on ne dérive
jamais vers le mode cours, pour ne pas casser le comportement historique.

La détection tient compte de la **continuité de session** (``in_course``) : une
relance courte de navigation (« continue », « passe aux exercices ») n'a de sens
que si l'élève est déjà dans un cours ; hors cours, elle retombe sur ``EXERCICE``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    EXERCICE = "exercice"
    COURS = "cours"
    #: L'élève demande à être interrogé (« teste-moi », « fais-moi un quiz »).
    QUIZ = "quiz"
    #: Question **sur** le service et non sur une notion : programme, chapitres
    #: couverts, méthode de travail, capacités de l'agent. Aucune recherche de
    #: contenu ne doit être lancée (cas QA #2, #3, #4).
    META = "meta"
    #: Le message n'est **qu'**une salutation (« Bonsoir », « Salut »). Il n'y a
    #: rien à chercher ni à socratiser : on accueille, puis on oriente vers ce
    #: que le corpus couvre réellement (cas QA #38, #41).
    SALUTATION = "salutation"
    #: L'élève demande qu'on lui **donne** un exercice à faire (« donne-moi un
    #: exercice sur le calcul intégral »). C'est l'inverse du tour ``EXERCICE``,
    #: où il travaille déjà sur un énoncé et demande de l'aide : ici il n'a pas
    #: d'énoncé, et la posture socratique n'a rien à retenir — elle ne peut que
    #: lui rappeler une règle générale, ce qu'il n'a pas demandé (cas QA #31).
    ENTRAINEMENT = "entrainement"


class Navigation(str, Enum):
    #: Démarrage explicite d'un cours (« explique-moi les nombres complexes »).
    START = "start"
    #: Avancer à la section suivante (« continue »).
    NEXT = "next"
    #: Revenir à la section précédente.
    PREV = "prev"
    #: Sauter à une section nommée (« passe aux exercices »). La cible est
    #: résolue par ``course_plan.resolve_goto`` à partir de la question brute.
    GOTO = "goto"


# --- Déclencheurs de démarrage d'un cours ------------------------------------
# Formulations par lesquelles un élève demande explicitement un enseignement.
_COURSE_START = re.compile(
    r"\b(?:"
    r"fais(?:[\s-]+moi)?\s+un\s+cours"
    r"|donne(?:[\s-]+moi)?\s+un\s+cours"
    r"|un\s+cours\s+sur"
    r"|cours\s+(?:sur|de|complet)"
    # Les variantes d'accord et d'infinitif comptent autant que la forme
    # canonique : « Expliques moi les dérivées » (cas QA #35) ne matchait NI
    # « explique\b » (le « s » colle au mot) NI « expliqu[ez]-(?:moi) » (l'espace
    # remplace le trait d'union). La phrase partait donc en posture socratique,
    # où le niveau 1 « rappelle la règle utile » s'appliquait à cinq extraits de
    # nombres complexes — d'où le sujet jamais demandé que la testeuse a vu
    # apparaître. Une faute d'accord ne doit pas changer de branche.
    # Les lookbehinds tiennent la frontière que le « s » avait ouverte : « Ça
    # fait 3 fois que TU M'expliques » (cas QA #20) est un constat sur les tours
    # précédents, pas une demande de cours. Sans eux, le correctif du #35
    # détournait le #20 — déjà clos — vers le mode cours.
    r"|(?<!m['’])(?<!me\s)(?<!tu\s)(?<!nous\s)(?<!vous\s)"
    r"explique[sz]?(?:[\s-]+(?:moi|nous))?\b"
    # L'infinitif n'a pas besoin du garde-fou ci-dessus et gagne à l'éviter :
    # « tu peux m'expliquer les intégrales ? » est bien une demande de cours,
    # alors que « tu m'expliques » n'en est pas une.
    r"|expliquer\b"
    r"|pr[ée]sentes?(?:[\s-]+moi)?\b"
    r"|pr[ée]senter\s+(?:le|la|les)\b"
    r"|enseignes?(?:[\s-]+moi)?\b"
    r"|apprends?(?:[\s-]+moi)?\b"
    r"|je\s+veux\s+(?:apprendre|comprendre|r[ée]viser|[ée]tudier)"
    r"|j['e]\s*aimerais\s+(?:apprendre|comprendre|r[ée]viser)"
    r"|initie(?:[\s-]+moi)?\b"
    r"|c['e]est\s+quoi\b"
    r"|qu['e]est[\s-]?ce\s+que\b"
    r")",
    re.IGNORECASE,
)

#: Incompréhension déclarée **suivie d'un déterminant** : « je ne comprends pas
#: LES dérivées », « j'ai rien compris AUX intégrales ». Le déterminant est exigé,
#: et c'est lui qui fait tout le travail : « je ne comprends pas » tout court, ou
#: « je ne comprends pas pourquoi », ne nomme rien et reste une difficulté sur
#: l'exercice en cours (cas QA #20).
_INCOMPREHENSION_DECLAREE = re.compile(
    r"\b(?:"
    r"je\s+(?:ne\s+)?comprends?\s+(?:pas|rien)"
    r"|j['e]\s*(?:n['e]\s*)?ai\s+(?:pas|rien)\s+compris"
    r"|j['e]\s*(?:y\s+)?pige\s+rien"
    r"|c['e]est\s+flou\s+pour\s+moi"
    r")"
    # Le déterminant, sous ses deux formes : pleine (« les dérivées ») ou élidée
    # (« l'intégration »), éventuellement précédée de la préposition.
    r"(?:"
    r"\s+(?:aux?|les|la|des|du|(?:[àa]|de|dans)\s+la)\s+"
    r"|\s+(?:le)\s+"
    r"|\s+(?:(?:[àa]|de|dans)\s+)?l['e]\s*"
    r")",
    re.IGNORECASE,
)

#: Ce qui, juste après cette tournure, désigne le **matériel du tour en cours**
#: et non une notion du programme : « je ne comprends pas la question », « …
#: l'énoncé », « … la correction ». Le défaut sûr du module est ``EXERCICE``, et
#: cette liste est ce qui l'applique — en cas de doute sur un mot, ne pas le
#: retirer d'ici : le laisser, c'est rester sur le comportement historique.
_MATERIEL_DU_TOUR = re.compile(
    r"^(?:question|[ée]nonc[ée]|exercice|probl[èe]me|[ée]tape|consigne|correction|"
    r"r[ée]ponse|solution|calcul|op[ée]ration|r[ée]sultat|explication|d[ée]monstration|"
    r"exemple|phrase|texte|ligne|partie|sujet|truc|machin|passage|indice|"
    r"remarque|chose|derni[èe]re|premi[èe]re)\b",
    re.IGNORECASE,
)


def declare_ne_pas_comprendre_une_notion(question: str) -> bool:
    """Vrai si l'élève déclare ne pas comprendre une **notion nommée**.

    « Je ne comprends pas les dérivées » est une demande d'explication, au même
    titre que « Je veux comprendre les dérivées » — que ``_COURSE_START``
    reconnaît déjà. Les deux phrases disent la même chose ; seule la seconde
    ouvrait un cours, et cette asymétrie est le cas QA #14 : la première partait
    en posture socratique, dont le niveau 1 prescrit de « rappeler la règle SANS
    l'appliquer », sur cinq extraits d'un chapitre étranger — d'où la
    reformulation à vide que rapporte la testeuse.

    Le mode cours répond mieux **et** dit la vérité : ``course_planner`` y lie le
    chapitre à la demande de l'élève par recoupement de titre
    (``resolve_chapitre``), et sur « dérivées » — absentes des chapitres indexés
    — la liaison échoue, ce qui injecte l'avertissement de couverture au lieu de
    laisser enseigner les nombres complexes à sa place.

    Deux bornes, toutes deux nécessaires :

    * une **notion doit être nommée** (le déterminant l'atteste). Sans elle, on
      reste sur l'exercice en cours, ce qu'exige le cas #20 ;
    * ce qui est nommé ne doit pas être le matériel du tour (« la question »,
      « l'énoncé », « la correction »).
    """
    correspondance = _INCOMPREHENSION_DECLAREE.search(question)
    if correspondance is None:
        return False
    reste = question[correspondance.end() :].lstrip(" '’")
    return bool(reste) and _MATERIEL_DU_TOUR.match(reste) is None


# --- Navigation à l'intérieur d'un cours en cours ----------------------------
_NAV_NEXT = re.compile(
    r"\b(?:continue[rz]?|suite|section\s+suivante|au?\s+suivant|"
    r"la\s+suite|poursuis|encha[îi]ne|passe\s+[àa]\s+la\s+suite|ok\s*,?\s*suite)\b",
    re.IGNORECASE,
)
_NAV_PREV = re.compile(
    r"\b(?:pr[ée]c[ée]dent[e]?|section\s+pr[ée]c[ée]dente|reviens|retour[\s-]+en[\s-]+arri[èe]re|"
    r"reviens\s+en\s+arri[èe]re)\b",
    re.IGNORECASE,
)
# Saut vers une section nommée : « passe aux exercices », « montre les exemples »,
# « et les définitions ? ». On matche le verbe/tournure + un mot de section
# reconnu par course_plan (la résolution fine du numéro de section y est faite).
_NAV_GOTO = re.compile(
    r"\b(?:passe[rz]?|va|aller|montre[\s-]?moi|donne[\s-]?moi|voir|"
    r"saute[rz]?|directement|plut[ôo]t)\b.*\b(?:"
    r"exercices?|exemples?|d[ée]finitions?|th[ée]or[èe]mes?|propri[ée]t[ée]s?|"
    r"m[ée]thodes?|erreurs?|astuces?|r[ée]sum[ée]|r[ée]vision|introduction|intro)\b",
    re.IGNORECASE,
)
# Mots de section employés seuls (« les exercices », « des exemples ? ») — utile
# uniquement en mode cours, où la référence est sans ambiguïté.
_SECTION_MENTION = re.compile(
    r"\b(?:exercices?|exemples?|d[ée]finitions?|th[ée]or[èe]mes?|propri[ée]t[ée]s?|"
    r"m[ée]thodes?|astuces?|r[ée]sum[ée]|r[ée]vision)\b",
    re.IGNORECASE,
)

# --- Sortie de secours du mode cours -----------------------------------------
# Un signal d'exercice FORT (demande de résolution/calcul) rompt la « collance »
# du mode cours : sans ça, un élève en plein cours qui tape « calcule … » resterait
# piégé en posture didactique au lieu de repartir sur le pipeline socratique
# (avec routage outil SymPy). Verbes impératifs de résolution uniquement — les
# tournures de difficulté (« je ne trouve pas », « je n'ai pas compris ») ne
# doivent PAS déclencher la sortie et rester dans le cours.
_EXERCISE_BREAKOUT = re.compile(
    r"\b(?:"
    r"calcule[rz]?|r[ée]sous|r[ée]soudre|resous|corrige[rz]?|factorise[rz]?|"
    r"d[ée]veloppe[rz]?|simplifie[rz]?|d[ée]montre[rz]?|d[ée]termine[rz]?|"
    r"montre\s+que|donne(?:[\s-]+moi)?\s+(?:la|ta)\s+(?:r[ée]ponse|solution|correction)"
    r")\b",
    re.IGNORECASE,
)


# --- Demande d'évaluation ----------------------------------------------------
# Formulations par lesquelles un élève demande à être interrogé. Volontairement
# étroit : ces tournures sont sans ambiguïté, et en cas de doute on retombe sur
# le défaut sûr (EXERCICE) plutôt que d'interroger quelqu'un qui n'a rien
# demandé. « quiz » est reconnu seul car le mot n'a pas d'autre usage ici.
_QUIZ_REQUEST = re.compile(
    r"\b(?:"
    r"quiz"
    r"|qcm"
    r"|teste?[\s-]?(?:moi|nous)"
    r"|interroge[\s-]?(?:moi|nous)"
    r"|[ée]value[\s-]?(?:moi|nous)"
    r"|pose[\s-]?(?:moi|nous)\s+(?:des|une|quelques)\s+questions?"
    r"|(?:fais|donne)(?:[\s-]+moi)?\s+(?:un|des)\s+(?:test|exercices?\s+d[e']\s*[ée]valuation)"
    r"|questionnaire"
    r"|vrai\s*[/ou-]+\s*faux"
    r")\b",
    re.IGNORECASE,
)


# --- Demande d'un exercice à faire -------------------------------------------
# « Donne-moi un exercice sur le calcul intégral » (cas QA #31). Le tour tombait
# en EXERCICE — le défaut — puis au niveau d'indice 1, dont la consigne est
# « Rappelle la règle utile SANS l'appliquer ». L'élève recevait donc une règle
# générale à la place de l'énoncé qu'il demandait, et l'insistance ne changeait
# rien : chaque relance repassait par la même consigne.
#
# La distinction que porte ce prédicat est celle-ci, et elle est structurelle :
# la posture socratique suppose que l'élève a **déjà** un énoncé sous les yeux —
# c'est ce qu'elle retient qui le fait chercher. Quand il n'en a pas, il n'y a
# rien à retenir, et lui refuser l'énoncé n'enseigne rien.

#: Verbes par lesquels on demande qu'on nous **donne** quelque chose.
_VERBE_DE_REMISE = (
    r"(?:donne|propose|file|sors|choisis|s[ée]lectionne|g[ée]n[èe]re|genere|"
    r"cr[ée]e|pr[ée]pare|trouve|fais|balance|montre)"
)

#: Déterminant **indéfini**, et c'est lui qui fait le tri : « donne-moi UN
#: exercice » réclame un énoncé, « corrige MON exercice » / « donne-moi LA
#: correction de l'exercice » parlent d'un énoncé déjà en main, qui relève de la
#: posture socratique inchangée. Exiger l'indéfini écarte donc les seconds sans
#: avoir à énumérer les tournures d'aide, toujours plus nombreuses.
_DETERMINANT_INDEFINI = (
    r"(?:un\s+autre|une\s+autre|encore\s+un|encore\s+une|d['’e]\s*autres|"
    r"quelques|plusieurs|des|un|une|deux|trois|\d+)"
)

#: Ce qu'on demande : un énoncé à traiter. « exemple » n'y figure PAS — un
#: exemple résolu est du matériel de cours, et le confondre avec un exercice
#: ferait basculer en entraînement des demandes d'explication.
_NOM_D_EXERCICE = (
    r"(?:exercices?|exos?|probl[èe]mes?|entra[îi]nements?|applications?|"
    r"questions?\s+type\s+bac|sujets?\s+d['’e]\s*entra[îi]nement)"
)

#: Adverbes qui s'intercalent entre le verbe et le déterminant sans changer ce
#: qui est demandé (« donne-moi PLUTÔT un exercice »). La liste est fermée à
#: dessein : accepter n'importe quel mot ferait entrer « montre-moi comment faire
#: un exercice », qui est une question de méthode et relève du mode cours.
_ADVERBE_INTERCALE = (
    r"(?:(?:plut[ôo]t|vraiment|maintenant|juste|simplement|encore|alors|donc|"
    r"d[ée]j[àa]|svp|stp)\s+){0,2}"
)

_DEMANDE_EXERCICE = re.compile(
    r"(?:"
    # « donne-moi un exercice », « propose deux exos », « fais-moi un problème »
    rf"\b{_VERBE_DE_REMISE}(?:[\s-]+(?:moi|nous))?\s+{_ADVERBE_INTERCALE}"
    rf"(?:{_DETERMINANT_INDEFINI})\s+(?:\w+\s+){{0,2}}?{_NOM_D_EXERCICE}\b"
    # « je veux un exercice », « peux-tu me proposer quelques exercices »
    rf"|\b(?:je\s+(?:veux|voudrais|souhaite)|j['’e]\s*aimerais|"
    rf"peux[\s-]?tu\s+(?:me\s+)?(?:donner|proposer)|"
    rf"pourrais[\s-]?tu\s+(?:me\s+)?(?:donner|proposer)|il\s+me\s+faut)\b"
    rf"[^?.!]{{0,40}}?\b(?:{_DETERMINANT_INDEFINI})\s+(?:\w+\s+){{0,2}}?{_NOM_D_EXERCICE}\b"
    # « un autre exercice », « encore un exo », « d'autres exercices » (relance)
    rf"|\b(?:un\s+autre|une\s+autre|encore\s+un|encore\s+une|d['’e]\s*autres)\s+"
    rf"(?:\w+\s+){{0,2}}?{_NOM_D_EXERCICE}\b"
    # Forme nominale en tête : « Exercice sur les suites numériques » (fixture
    # positive #52) — sans verbe, mais sans ambiguïté non plus.
    rf"|^\s*{_NOM_D_EXERCICE}\s+(?:sur|de|d['’e]\s*|en|autour\s+de)\b"
    # « entraîne-moi », « je veux m'entraîner »
    r"|\bentra[îi]ne[\s-]?(?:moi|nous)\b"
    r"|\bje\s+(?:veux|voudrais)\s+m['’e]\s*(?:entra[îi]ner|exercer|entrainer)\b"
    r"|\bje\s+veux\s+(?:faire|travailler)\s+(?:des|quelques|plusieurs)\s+"
    rf"{_NOM_D_EXERCICE}\b"
    r")",
    re.IGNORECASE,
)


def demande_un_exercice(question: str) -> bool:
    """Vrai si l'élève demande qu'on lui **fournisse** un énoncé à traiter.

    Le prédicat est volontairement exigeant sur le déterminant (cf.
    :data:`_DETERMINANT_INDEFINI`) : « corrige mon exercice », « je bloque sur
    cet exercice » ou « donne-moi la correction de l'exercice 3 » parlent d'un
    énoncé que l'élève a déjà, et doivent rester dans la posture socratique.
    """
    return bool(_DEMANDE_EXERCICE.search(question))


# --- Questions méta ----------------------------------------------------------
# Deux niveaux, et la distinction est nécessaire : « donne-moi les astuces »
# désigne la section « Astuces » quand on est DANS un cours (cf. _SECTION_MENTION
# et test_intent.test_section_mention_inside_course_is_goto), mais une demande de
# méthode de travail hors cours. Les motifs sans ambiguïté priment partout ; les
# ambigus ne sont consultés qu'en dehors d'un cours.

#: Reconnu en toute circonstance : porte sur la couverture du service, jamais
#: sur une notion. « au programme », « quels chapitres », « que sais-tu faire ».
_META_TOUJOURS = re.compile(
    r"(?:"
    r"\b(?:mon|le|du|au|ton)\s+programme\b"
    r"|\bprogramme\s+(?:de\s+(?:cette\s+ann[ée]e|l'ann[ée]e|maths?|math[ée]matiques)|scolaire|officiel)"
    r"|\b(?:quels?|quelles?)\s+(?:sont\s+)?(?:les\s+)?(?:grands\s+)?"
    r"(?:chapitres?|le[çc]ons?|th[èe]mes?|notions?|sujets?)\b"
    r"|\b(?:chapitres?|le[çc]ons?)\s+(?:disponibles?|couverts?|index[ée]s?|au\s+programme)\b"
    r"|\bsur\s+quo?[ie]\s+(?:peux[\s-]?tu|pouvez[\s-]?vous|tu\s+peux)\b"
    r"|\bsur\s+quels?\s+(?:chapitres?|le[çc]ons?|sujets?)\b"
    r"|\bqu['e]\s*est[\s-]?ce\s+que\s+tu\s+(?:sais|peux|as)\b"
    r"|\bque\s+sais[\s-]?tu\s+faire\b"
    r"|\b(?:comment|qui)\s+(?:tu\s+)?fonctionnes?\b"
    r"|\btu\s+sers\s+[àa]\s+quoi\b"
    r")",
    re.IGNORECASE,
)

#: Sous-ensemble du méta : l'élève demande **l'inventaire** de ce qui est couvert
#: (« liste-moi les chapitres », « quel est mon programme »). Ce tour-là reçoit
#: une réponse écrite par le code (cf. ``orientation.reponse_catalogue``), parce
#: que l'exigence porte sur l'exactitude d'une liste et non sur une tournure.
#:
#: La forme impérative manquait, et elle a coûté cher : « Listes moi les
#: chapitres du cours de maths en terminale S1 » (cas QA #26) tombait en mode
#: COURS — le mot « cours » y déclenchait ``_COURSE_START`` — donc en ouverture
#: de chapitre sur une demande d'inventaire. D'où les « réponses de qualité
#: variable » d'une reformulation à l'autre : ce n'était pas la même branche.
_META_CATALOGUE = re.compile(
    r"(?:"
    r"\b(?:mon|le|du|au|ton)\s+programme\b"
    r"|\bprogramme\s+(?:de\s+(?:cette\s+ann[ée]e|l'ann[ée]e|maths?|math[ée]matiques)|scolaire|officiel)"
    r"|\b(?:quels?|quelles?)\s+(?:sont\s+)?(?:les\s+)?(?:grands\s+)?"
    r"(?:chapitres?|le[çc]ons?|th[èe]mes?|notions?|sujets?)\b"
    r"|\b(?:chapitres?|le[çc]ons?)\s+(?:disponibles?|couverts?|index[ée]s?|au\s+programme)\b"
    r"|\bsur\s+quo?[ie]\s+(?:peux[\s-]?tu|pouvez[\s-]?vous|tu\s+peux)\b"
    r"|\bsur\s+quels?\s+(?:chapitres?|le[çc]ons?|sujets?)\b"
    # Forme impérative : « liste-moi les chapitres », « donne-moi la liste des
    # leçons », « montre-moi tes chapitres ».
    r"|\b(?:listes?|liste[\s-]?(?:moi|nous)|[ée]num[èe]re|donne[\s-]?(?:moi|nous)?\s+la\s+liste|"
    r"montre[\s-]?(?:moi|nous)?|dis[\s-]?(?:moi|nous)?|c['’e]est\s+quoi)\b"
    r"[^?.!]{0,30}?\b(?:chapitres?|le[çc]ons?|th[èe]mes?)\b"
    r"|\bqu['’e]\s*est[\s-]?ce\s+que\s+tu\s+(?:as|couvres?)\b"
    r")",
    re.IGNORECASE,
)


def demande_le_catalogue(question: str) -> bool:
    """Vrai si l'élève demande l'inventaire des chapitres couverts."""
    return bool(_META_CATALOGUE.search(question))


#: Demande d'aide **sans objet nommé** : « aide-moi à devenir meilleure en
#: mathématiques » (cas QA #27). Ni exercice (aucun énoncé), ni cours (aucun
#: chapitre nommé) : la réponse utile est une question de clarification, adossée
#: aux chapitres réellement disponibles. Sans cette branche, la phrase tombait
#: en posture socratique de niveau 1 sur cinq extraits pris au hasard, d'où la
#: relance sans rapport (« qu'est-ce que tu veux faire avec cette équation ? »).
#:
#: Le motif exige la **progression** comme objet ; il laisse donc passer
#: « aide-moi sur cet exercice » et « aide-moi à calculer cette intégrale », qui
#: nomment leur objet et relèvent de la posture socratique inchangée.
_DEMANDE_OUVERTE = re.compile(
    r"(?:"
    r"\b(?:aide[\s-]?(?:moi|nous)|aidez[\s-]?(?:moi|nous)|j['’e]\s*ai\s+besoin\s+d['’e]\s*aide)\b"
    r"\s*(?:[àa]\s+|pour\s+|de\s+)?"
    r"(?:devenir|[êe]tre|progresser|m['’e]\s*am[ée]liorer|avoir|r[ée]ussir|remonter|"
    r"me\s+perfectionner|travailler)?"
    r"[^?.!]{0,30}?\b(?:meilleur[e]?s?|bon(?:ne)?s?|fort[e]?s?|progresser|"
    r"am[ée]liorer|moyenne|niveau|r[ée]ussir)\b"
    r"|\bje\s+(?:veux|voudrais|souhaite|aimerais)\s+(?:devenir|[êe]tre)\s+"
    r"(?:meilleur[e]?|bon(?:ne)?|fort[e]?)\b"
    r"|\bje\s+veux\s+(?:progresser|m['’e]\s*am[ée]liorer)\b"
    r"|\bcomment\s+(?:devenir|[êe]tre)\s+(?:meilleur[e]?|bon(?:ne)?|fort[e]?)\b"
    r")",
    re.IGNORECASE,
)


#: Question générale **sur la discipline elle-même** — « à quoi servent les
#: mathématiques ? » (cas QA #43). Ni exercice (rien à résoudre) ni cours (aucun
#: chapitre nommé) : c'est une question d'orientation, à laquelle la branche
#: méta répond en s'appuyant sur ce que l'agent couvre réellement.
#:
#: Le motif exige la **discipline** comme objet, jamais une notion : « à quoi ça
#: sert les nombres complexes ? » reste une question de contenu et doit continuer
#: d'atteindre le corpus (elle est déjà citée comme frontière à tenir dans D5).
_QUESTION_SUR_LA_DISCIPLINE = re.compile(
    r"(?:"
    r"\b(?:[àa]\s+quoi|pourquoi)\b[^?.!]{0,40}?"
    r"\b(?:sert|servent|[ée]tudier|apprendre|faire|travailler|utile)\b"
    r"[^?.!]{0,20}?\b(?:les\s+)?math(?:s|[ée]matiques?)\b"
    r"|\b(?:les\s+)?math(?:s|[ée]matiques?)\b[^?.!]{0,20}?"
    r"\b(?:[çc]a\s+)?(?:sert|servent)\s+[àa]\s+quoi\b"
    r"|\b(?:l['’e]\s*)?(?:utilit[ée]|int[ée]r[êe]t)\s+des?\s+math(?:s|[ée]matiques?)\b"
    r")",
    re.IGNORECASE,
)


def est_une_question_sur_la_discipline(question: str) -> bool:
    """Vrai si l'élève interroge l'utilité des mathématiques en général."""
    return bool(_QUESTION_SUR_LA_DISCIPLINE.search(question))


def est_une_demande_ouverte(question: str) -> bool:
    """Vrai si l'élève demande de l'aide sans nommer de notion ni d'exercice."""
    return bool(_DEMANDE_OUVERTE.search(question))


#: Reconnu **hors cours** seulement : demande de méthode de travail. En cours,
#: ces mêmes mots désignent une section du plan et restent une navigation.
_META_HORS_COURS = re.compile(
    r"(?:"
    r"\b(?:astuces?|conseils?|m[ée]thodes?|techniques?)\b[^?.!]{0,40}?"
    r"\b(?:pour|afin\s+de)\b[^?.!]{0,40}?"
    r"\b(?:am[ée]liorer|progresser|r[ée]viser|travailler|r[ée]ussir|mieux)\b"
    r"|\b(?:comment|quelle?s?)\b[^?.!]{0,30}?"
    r"\b(?:r[ée]viser|progresser|m['e]am[ée]liorer|mieux\s+travailler|bien\s+travailler)\b"
    r"|\bdes\s+(?:astuces?|conseils?)\b"
    r")",
    re.IGNORECASE,
)


# --- Salutations -------------------------------------------------------------
# Un « Bonsoir » tombait en EXERCICE, et comme il fait moins de 4 tokens,
# `diagnose_hint_level` le classait au niveau 0, dont la consigne dit
# « Reformule la question de l'élève […] n'apporte AUCUNE information nouvelle ».
# L'enchaînement sur une question de vérification que rapportent les testeurs
# était donc prescrit, pas accidentel (cas QA #38 et #41).
_SALUTATION = re.compile(
    r"\b(?:bonjour|bonsoir|salut|coucou|bjr|bsr|slt|cc|hello|hi|hey|yo|"
    r"bonne\s+(?:journ[ée]e|soir[ée]e)|re)\b",
    re.IGNORECASE,
)

#: Politesses et formules de civilité qui accompagnent une salutation sans rien
#: y ajouter de substantiel : « Bonsoir, ça va ? » reste une salutation.
_CIVILITES = re.compile(
    r"\b(?:[çc]a\s+va|comment\s+(?:vas[\s-]?tu|allez[\s-]?vous|tu\s+vas)|"
    r"tu\s+vas\s+bien|vous\s+allez\s+bien|merci|s['e]il\s+(?:te|vous)\s+pla[îi]t|"
    r"stp|svp|et\s+toi|moi\s+c['e]est\s+\w+|je\s+m['e]appelle\s+\w+|"
    r"le\s+tuteur|monsieur|madame|prof(?:esseur)?)\b",
    re.IGNORECASE,
)

#: Ce qui reste après retrait des salutations et civilités. Tout caractère
#: alphanumérique résiduel signale une vraie demande.
_RESIDU_SIGNIFIANT = re.compile(r"[^\W_]", re.UNICODE)


def est_une_salutation(question: str) -> bool:
    """Vrai si le message n'est **rien d'autre** qu'une salutation.

    La condition « rien d'autre » est le cœur du prédicat, et pas un raffinement :
    « Salut, comment on calcule le module d'un nombre complexe ? » est une vraie
    question, et l'accueillir sans y répondre reproduirait le défaut qu'on
    corrige, à l'envers. On retire donc les salutations et les civilités, puis on
    exige que le résidu ne porte plus aucun caractère alphanumérique.
    """
    if not _SALUTATION.search(question):
        return False
    residu = _SALUTATION.sub(" ", question)
    residu = _CIVILITES.sub(" ", residu)
    return not _RESIDU_SIGNIFIANT.search(residu)


def is_meta_request(question: str, *, in_course: bool = False) -> bool:
    """Vrai si la question porte sur le service plutôt que sur une notion."""
    if _META_TOUJOURS.search(question):
        return True
    return not in_course and bool(_META_HORS_COURS.search(question))


def is_quiz_request(question: str) -> bool:
    """Vrai si l'élève demande explicitement à être interrogé."""
    return bool(_QUIZ_REQUEST.search(question))


def is_exercise_breakout(question: str) -> bool:
    """Vrai si la question est une demande de résolution qui doit sortir du cours."""
    return bool(_EXERCISE_BREAKOUT.search(question))


@dataclass
class IntentDecision:
    intent: Intent
    reason: str
    #: Non ``None`` uniquement quand ``intent == COURS``.
    navigation: Navigation | None = None


def _detect_navigation(question: str, *, in_course: bool) -> Navigation | None:
    """Type de navigation cours détecté, ou ``None``.

    ``START`` est reconnu partout (un élève peut ouvrir un cours à tout moment) ;
    ``NEXT``/``PREV``/``GOTO`` ne sont interprétés **que** si l'on est déjà dans
    un cours — sinon un simple « continue » n'a pas de section à faire avancer.
    """
    if _COURSE_START.search(question):
        return Navigation.START
    if not in_course:
        # Une incompréhension déclarée n'ouvre un cours que **hors** cours. En
        # plein cours, « je n'ai pas compris le module » est une sous-question
        # sur la section courante, pas une demande de repartir de zéro : c'est
        # la continuité que gèrent déjà les branches ci-dessous.
        if declare_ne_pas_comprendre_une_notion(question):
            return Navigation.START
        return None
    if _NAV_NEXT.search(question):
        return Navigation.NEXT
    if _NAV_PREV.search(question):
        return Navigation.PREV
    # Saut *explicite* (verbe + section) uniquement ; la simple mention d'un mot
    # de section (« et les exercices ? ») est traitée à part dans classify_intent,
    # APRÈS la sortie de secours, pour ne pas capturer « corrige mon exercice ».
    if _NAV_GOTO.search(question):
        return Navigation.GOTO
    return None


def classify_intent(question: str, *, in_course: bool = False) -> IntentDecision:
    """Décide entre ``EXERCICE`` (défaut sûr) et ``COURS``.

    ``in_course`` indique que le dernier tour de la conversation était déjà en
    mode cours (reconstruit par l'appelant depuis la trace persistée). Dans ce
    cas, une relance sans marqueur explicite reste dans le cours (poursuite du
    fil), sur la section courante.
    """
    # Un message qui n'est qu'une salutation passe avant tout le reste : il n'y
    # a ni notion à chercher, ni exercice à socratiser. Le prédicat exige que le
    # message ne contienne rien d'autre, donc aucune vraie demande n'est
    # absorbée ici — « Salut, calcule 1+1 » n'est pas une salutation.
    if est_une_salutation(question):
        return IntentDecision(Intent.SALUTATION, "salutation seule", None)

    # Une demande d'évaluation prime sur tout le reste, y compris sur la
    # continuité d'un cours : « teste-moi » pendant un cours veut bien dire
    # « interroge-moi maintenant », pas « continue à m'expliquer ».
    if is_quiz_request(question):
        return IntentDecision(Intent.QUIZ, "demande explicite d'évaluation", None)

    # Une question méta sans ambiguïté prime sur tout : demander « quels
    # chapitres as-tu ? » n'est pas demander un cours sur les chapitres. La
    # demande d'inventaire est distinguée ici parce que le nœud méta lui sert
    # une réponse déterministe (cas QA #26).
    if demande_le_catalogue(question):
        return IntentDecision(Intent.META, "demande d'inventaire des chapitres", None)
    if _META_TOUJOURS.search(question):
        return IntentDecision(Intent.META, "question sur le service (programme, couverture)", None)

    # Demande d'un énoncé à traiter — **hors cours seulement**. En plein cours,
    # « donne-moi un exercice » désigne la section « Exercices » du chapitre en
    # train d'être enseigné, et le saut de section y répond déjà (cf.
    # ``_NAV_GOTO`` et test_section_mention_inside_course_is_goto) : le détourner
    # ici couperait le cours au lieu de le servir.
    if not in_course and demande_un_exercice(question):
        return IntentDecision(Intent.ENTRAINEMENT, "demande d'un exercice à faire", None)

    nav = _detect_navigation(question, in_course=in_course)

    if nav == Navigation.START:
        return IntentDecision(Intent.COURS, "demande explicite de cours", Navigation.START)

    if in_course:
        # Navigation explicite (suite / saut avec verbe) → on avance dans le cours.
        if nav is not None:
            return IntentDecision(Intent.COURS, f"poursuite du cours ({nav.value})", nav)
        # Une demande de résolution explicite rompt le mode cours — prioritaire sur
        # une simple mention de section (« corrige mon exercice » n'est pas un saut).
        if is_exercise_breakout(question):
            return IntentDecision(Intent.EXERCICE, "sortie du cours (demande de résolution)", None)
        # Mention seule d'une section (« et les définitions ? ») → saut implicite.
        if _SECTION_MENTION.search(question):
            return IntentDecision(Intent.COURS, "poursuite du cours (goto)", Navigation.GOTO)
        return IntentDecision(Intent.COURS, "poursuite du cours", None)

    # Hors cours seulement : « aide-moi à devenir meilleure en maths » n'a ni
    # énoncé ni chapitre à quoi se rattacher ; en plein cours, la même phrase
    # porte sur la section en train d'être enseignée (cas QA #27).
    if est_une_demande_ouverte(question):
        return IntentDecision(Intent.META, "demande d'aide sans objet nommé", None)

    # « À quoi servent les mathématiques ? » : question sur la discipline, pas
    # sur une notion. Sans cette branche, elle partait en posture socratique sur
    # cinq extraits pris au hasard, et la relance finale sortait de nulle part
    # (cas QA #43). Hors cours seulement : en plein cours, la même question est
    # une digression que la section en train d'être enseignée absorbe.
    if est_une_question_sur_la_discipline(question):
        return IntentDecision(Intent.META, "question sur l'utilité de la discipline", None)

    # Hors cours seulement : « des astuces pour progresser » est une demande de
    # méthode, alors qu'en cours les mêmes mots visent la section « Astuces ».
    if _META_HORS_COURS.search(question):
        return IntentDecision(Intent.META, "question sur la méthode de travail", None)

    return IntentDecision(Intent.EXERCICE, "défaut (résolution d'exercice)", None)
