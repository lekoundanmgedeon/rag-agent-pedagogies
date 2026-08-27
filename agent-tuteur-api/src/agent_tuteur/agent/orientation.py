"""Réponses d'orientation **écrites par le code** — le catalogue des chapitres.

Pourquoi pas le modèle. Le cas QA #26 rapporte des réponses « de qualité
variable » à une même question posée trois fois : « liste-moi les chapitres du
cours de maths ». Deux causes s'y superposaient — un mauvais routage (la phrase
tombait en mode *cours* à cause du mot « cours ») et, une fois ce routage
corrigé, la variabilité propre à toute prose échantillonnée.

La doctrine appliquée ici est celle de la décision D5 : quand l'exigence porte
sur **ce qui doit être dit** plutôt que sur la manière, on sort le texte de la
génération. Un inventaire de chapitres n'a aucune raison d'être reformulé à
chaque fois : il doit être exact, complet, et identique d'un tour à l'autre.

Effet de bord recherché : les règles n°3 et n°4 deviennent structurelles sur ce
tour. Le texte ne peut pas inventer un chapitre absent du store, ni taire un
chapitre présent, ni prétendre connaître le programme scolaire de l'élève.
"""

from __future__ import annotations

#: Ouverture commune : ce que l'agent ne sait PAS vient d'abord, parce que c'est
#: la question posée (« mon programme ») et que l'y confondre avec sa
#: couverture serait précisément l'hallucination de contexte élève (règle n°3).
_PREAMBULE = (
    "Je ne connais pas le programme officiel de ton établissement — je ne peux "
    "te parler que des leçons dont je dispose."
)

_SANS_CHAPITRE = (
    f"{_PREAMBULE}\n\n"
    "Et pour l'instant, je n'ai aucune leçon indexée pour ce cadre : je ne peux "
    "donc te proposer aucun chapitre. Signale-le à ton enseignant ou à "
    "l'administrateur de la plateforme, c'est à eux d'ajouter les leçons."
)

_RELANCE = (
    "Sur lequel veux-tu travailler ? Je peux t'en faire le cours section par "
    "section, te donner un exercice à chercher, ou t'interroger dessus."
)


def reponse_catalogue(chapitres: list[str]) -> str:
    """Inventaire des chapitres disponibles, mot pour mot identique à chaque appel.

    ``chapitres`` vient du store vectoriel (``HybridRetriever.catalogue``), déjà
    filtré par le cadre curriculaire : la liste rendue est donc celle que la
    recherche saura réellement servir ensuite. Proposer ici ce qui serait refusé
    au tour suivant recréerait le décalage du cas #28.
    """
    if not chapitres:
        return _SANS_CHAPITRE

    nombre = len(chapitres)
    entete = (
        f"{_PREAMBULE} En voici {nombre} pour l'instant :"
        if nombre > 1
        else f"{_PREAMBULE} J'en ai une pour l'instant :"
    )
    lignes = "\n".join(f"- {chapitre}" for chapitre in chapitres)
    return f"{entete}\n\n{lignes}\n\n{_RELANCE}"


#: Nombre de questions de l'élève reprises dans le récapitulatif de session.
MAX_QUESTIONS_RESUMEES = 10

#: Longueur à laquelle une question est tronquée dans le récapitulatif.
MAX_CARACTERES_PAR_QUESTION = 120


def reponse_resume_session(memoire, historique: list[dict] | None) -> str:
    """Récapitulatif de la session en cours, écrit par le code (cas QA #25).

    Le testeur demandait « résume-moi toutes les questions que je viens de poser
    et notre session ». Deux raisons de ne pas le faire rédiger par le modèle,
    et elles se renforcent : un récapitulatif se juge à son **exactitude**, et
    c'est précisément le genre de texte où un modèle ajoute une question qui n'a
    jamais été posée — l'hallucination de contexte que la règle n°3 interdit.

    Tout ce qui figure ici vient donc des messages réellement persistés et des
    traces des tours joués : rien n'est déduit, rien n'est reformulé.
    """
    questions = [
        (m.get("content") or "").strip()
        for m in (historique or [])
        if m.get("role") == "user" and (m.get("content") or "").strip()
    ]
    if not questions:
        return (
            "Notre échange vient de commencer : tu ne m'as encore rien demandé, "
            "je n'ai donc rien à récapituler. Dis-moi sur quoi tu veux travailler "
            "et nous ferons le point quand tu voudras."
        )

    lignes = [f"Voici le point sur notre session{f', {memoire.prenom}' if memoire.prenom else ''} :", ""]

    retenues = questions[-MAX_QUESTIONS_RESUMEES:]
    if len(questions) > len(retenues):
        lignes.append(
            f"**Tes questions** (les {len(retenues)} dernières sur {len(questions)}) :"
        )
    elif len(retenues) == 1:
        # Accord au singulier : « Tes question » se lisait dans la réponse
        # servie à l'élève — un texte écrit par le code n'a aucune excuse pour
        # une faute d'accord, puisqu'il ne varie pas.
        lignes.append("**Ta question** :")
    else:
        lignes.append(f"**Tes questions** ({len(retenues)}) :")
    for numero, question in enumerate(retenues, start=1):
        if len(question) > MAX_CARACTERES_PAR_QUESTION:
            question = question[:MAX_CARACTERES_PAR_QUESTION].rstrip() + "…"
        lignes.append(f"{numero}. {question}")

    if memoire.chapitres:
        lignes += ["", "**Chapitres travaillés** : " + ", ".join(memoire.chapitres) + "."]
    if memoire.dernier_exercice:
        lignes += ["", "**Un exercice t'a été proposé** ; il reste à le chercher si ce n'est pas fait."]

    lignes += [
        "",
        "Pour garder une trace écrite, utilise le bouton « Exporter » de la "
        "conversation : il enregistre l'échange sur ton appareil, et ton "
        "navigateur peut en faire un PDF depuis la fenêtre d'impression.",
        "",
        "On continue ? Dis-moi sur quoi tu veux travailler maintenant.",
    ]
    return "\n".join(lignes)


def reponse_envoi_de_fichier() -> str:
    """Réponse à « puis-je uploader une capture d'écran ? » (cas QA #24).

    Le testeur a reçu une réponse hors-sujet sur LaTeX. Ce qu'il fallait dire
    tient en deux phrases, et c'est une question de **capacité** : l'agent ne
    lit pas d'image aujourd'hui. Le texte est donc écrit par le code — une
    capacité annoncée doit être exacte, et un modèle qui improvise là-dessus
    promet un jour ce qu'il ne sait pas faire.

    Aucune promesse de fonctionnalité future : ce que deviendra l'upload
    d'images relève d'un arbitrage produit (DECISIONS.md, D9), pas d'une phrase
    dite à un élève.
    """
    return (
        "Je ne sais pas encore lire les images : ni capture d'écran, ni photo, "
        "ni PDF. Je ne peux travailler que sur du texte.\n\n"
        "Le plus simple : recopie l'énoncé ici, même approximativement. Tu peux "
        "écrire les formules en toutes lettres (« racine de x au carré plus 1 ») "
        "ou en LaTeX si tu connais — je m'y retrouverai. Si l'énoncé est long, "
        "envoie-moi seulement la question qui te bloque.\n\n"
        "Et si quelque chose dans l'énoncé est illisible ou ambigu, dis-le moi : "
        "je préfère te poser une question que deviner."
    )
