"""Génère le rapport de clôture du backlog QA au format .docx.

Lancer depuis la racine du dépôt : ``.venv/bin/python qa/generer_rapport_docx.py``
(dépendance : ``python-docx``, déjà présent dans le venv du projet).

Le tableau d'inventaire est relu à chaque exécution depuis ``qa_cases_all.json`` et
``qa_status.json`` : le document ne peut donc pas diverger du suivi. Les textes de
synthèse, eux, sont écrits ici — ils resteront à relire si le backlog rouvre.

Le document est destiné aux réunions techniques : il est donc structuré avec de
vrais styles de titre (le volet Navigation de Word fonctionne), une table des
matières qui se met à jour à l'ouverture, un tableau d'inventaire trié, et des
en-têtes/pieds de page. Les couleurs reprennent celles du récapitulatif publié.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

#: qa/generer_rapport_docx.py -> qa -> racine du dépôt.
DEPOT = Path(__file__).resolve().parents[1]
SORTIE = DEPOT / "qa" / "Cloture_backlog_QA_Nuru_2026-08-27.docx"

ENCRE = RGBColor(0x10, 0x1A, 0x28)
GRIS = RGBColor(0x5D, 0x6C, 0x80)
PEN = RGBColor(0xA3, 0x2B, 0x36)
CLOS = RGBColor(0x1C, 0x7A, 0x5E)
FILET = "DDE3EA"

SERIF = "Cambria"
SANS = "Calibri"
MONO = "Consolas"


# --- petits utilitaires de mise en forme -------------------------------------
def style_de_base(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = SANS
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = ENCRE
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for nom, taille, couleur, serif in (
        ("Heading 1", 18, ENCRE, True),
        ("Heading 2", 13.5, ENCRE, True),
        ("Heading 3", 11.5, ENCRE, False),
    ):
        st = doc.styles[nom]
        st.font.name = SERIF if serif else SANS
        st.font.size = Pt(taille)
        st.font.bold = not serif
        st.font.color.rgb = couleur
        st.paragraph_format.space_before = Pt(16 if nom == "Heading 1" else 12)
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.keep_with_next = True


def para(doc, texte="", *, style=None, taille=None, couleur=None, italique=False,
         gras=False, police=None, espace_apres=None, align=None):
    p = doc.add_paragraph(style=style)
    if texte:
        r = p.add_run(texte)
        r.italic = italique
        r.bold = gras
        if taille:
            r.font.size = Pt(taille)
        if couleur:
            r.font.color.rgb = couleur
        if police:
            r.font.name = police
    if espace_apres is not None:
        p.paragraph_format.space_after = Pt(espace_apres)
    if align is not None:
        p.alignment = align
    return p


def riche(doc, morceaux, *, style=None, espace_apres=None, gauche=None):
    """Paragraphe composé de (texte, {gras|italique|mono|couleur}) successifs."""
    p = doc.add_paragraph(style=style)
    for texte, options in morceaux:
        r = p.add_run(texte)
        r.bold = options.get("gras", False)
        r.italic = options.get("italique", False)
        if options.get("mono"):
            r.font.name = MONO
            r.font.size = Pt(9.5)
        if "couleur" in options:
            r.font.color.rgb = options["couleur"]
        if "taille" in options:
            r.font.size = Pt(options["taille"])
    if espace_apres is not None:
        p.paragraph_format.space_after = Pt(espace_apres)
    if gauche is not None:
        p.paragraph_format.left_indent = Cm(gauche)
    return p


def filet(paragraphe, couleur=FILET, taille=6, position="bottom") -> None:
    pPr = paragraphe._p.get_or_add_pPr()
    bordures = OxmlElement("w:pBdr")
    bord = OxmlElement(f"w:{position}")
    bord.set(qn("w:val"), "single")
    bord.set(qn("w:sz"), str(taille))
    bord.set(qn("w:space"), "6")
    bord.set(qn("w:color"), couleur)
    bordures.append(bord)
    pPr.append(bordures)


def fond(cellule, couleur_hex: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), couleur_hex)
    cellule._tc.get_or_add_tcPr().append(shd)


def champ(paragraphe, instruction: str) -> None:
    """Insère un champ Word (TOC, numéro de page…)."""
    debut = OxmlElement("w:fldChar")
    debut.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separateur = OxmlElement("w:fldChar")
    separateur.set(qn("w:fldCharType"), "separate")
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    run = paragraphe.add_run()._r
    for element in (debut, instr, separateur, fin):
        run.append(element)


def maj_champs_a_l_ouverture(doc: Document) -> None:
    """Word propose alors de mettre la table des matières à jour tout seul."""
    parametres = doc.settings.element
    maj = OxmlElement("w:updateFields")
    maj.set(qn("w:val"), "true")
    parametres.append(maj)


# --- construction du document ------------------------------------------------
doc = Document()
style_de_base(doc)

section = doc.sections[0]
section.page_width, section.page_height = Cm(21), Cm(29.7)
for cote in ("left_margin", "right_margin"):
    setattr(section, cote, Cm(2.2))
section.top_margin, section.bottom_margin = Cm(2.0), Cm(2.0)

# En-tête et pied de page
entete = section.header.paragraphs[0]
entete.text = "Agent pédagogique Nuru — clôture du backlog QA"
entete.runs[0].font.size = Pt(8.5)
entete.runs[0].font.color.rgb = GRIS
entete.alignment = WD_ALIGN_PARAGRAPH.RIGHT

pied = section.footer.paragraphs[0]
pied.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = pied.add_run("Page ")
r.font.size, r.font.color.rgb = Pt(8.5), GRIS
champ(pied, "PAGE")
r = pied.add_run(" sur ")
r.font.size, r.font.color.rgb = Pt(8.5), GRIS
champ(pied, "NUMPAGES")

# --- page de garde -----------------------------------------------------------
p = para(doc, "Round de testing · 8 testeurs · 48 retours exploitables",
         taille=9.5, couleur=GRIS, espace_apres=2)
p.runs[0].font.name = MONO

titre = doc.add_paragraph(style="Heading 1")
run = titre.add_run("Clôture du backlog QA")
run.font.size = Pt(30)
run.font.name = SERIF
titre.paragraph_format.space_before = Pt(4)
titre.paragraph_format.space_after = Pt(4)

p = para(doc,
         "Ce qui a été corrigé, par cause racine — et les quatre points qui attendent "
         "une décision.",
         taille=12, couleur=GRIS, italique=True, espace_apres=10)
p.runs[0].font.name = SERIF
filet(p)

riche(doc, [
    ("Document de travail — réunion technique du ", {}),
    ("27 août 2026", {"gras": True}),
    (".  Source de vérité : ", {}),
    ("qa/qa_status.json", {"mono": True}),
    (" (cause racine, correctif et preuve, cas par cas) et ", {}),
    ("qa/DECISIONS.md", {"mono": True}),
    (" (arbitrages).", {}),
], espace_apres=14)

# Synthèse chiffrée
tab = doc.add_table(rows=2, cols=5)
tab.style = "Table Grid"
tab.alignment = WD_TABLE_ALIGNMENT.CENTER
chiffres = [
    ("48", "cas au backlog", ENCRE),
    ("46", "corrigés", CLOS),
    ("1", "vérifié", CLOS),
    ("1", "non corrigé", GRIS),
    ("4", "décisions ouvertes", PEN),
]
for i, (valeur, libelle, couleur) in enumerate(chiffres):
    haut = tab.cell(0, i).paragraphs[0]
    haut.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = haut.add_run(valeur)
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(22), True, couleur, MONO
    bas = tab.cell(1, i).paragraphs[0]
    bas.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = bas.add_run(libelle)
    r.font.size, r.font.color.rgb = Pt(8.5), GRIS
    fond(tab.cell(0, i), "FFFFFF")
    fond(tab.cell(1, i), "F4F6F8")

para(doc, "", espace_apres=4)
riche(doc, [
    ("Couverture par priorité : ", {}),
    ("Critique 7/7", {"gras": True}), ("  ·  ", {"couleur": GRIS}),
    ("Haute 14/14", {"gras": True}), ("  ·  ", {"couleur": GRIS}),
    ("Moyenne 21/21", {"gras": True}), ("  ·  ", {"couleur": GRIS}),
    ("Basse 6/6", {"gras": True}),
], espace_apres=14)

# Table des matières
p = para(doc, "Sommaire", taille=13.5, gras=True, espace_apres=2)
p.runs[0].font.name = SERIF
p_toc = doc.add_paragraph()
champ(p_toc, r'TOC \o "1-2" \h \z \u')
para(doc, "(Si le sommaire est vide : clic droit → « Mettre à jour les champs ».)",
     taille=8.5, couleur=GRIS, italique=True)

doc.add_page_break()

# --- 1. Ce qui demande votre attention ---------------------------------------
h = doc.add_paragraph(style="Heading 1")
h.add_run("Ce qui demande votre attention")
filet(h, couleur="A32B36", taille=12, position="top")

para(doc,
     "Aucun de ces points ne bloque la démo, et aucun n'est un reste de travail "
     "technique : ce sont des arbitrages qui reviennent au porteur du projet, plus "
     "deux gestes d'exploitation à programmer.",
     couleur=GRIS, espace_apres=10)

decisions = [
    ("D2 — ouverte", "Comment juger la prose que le modèle écrit ?",
     "Les tests savent vérifier les décisions du pipeline (routage, seuils, appels "
     "d'outils), jamais le texte produit : un modèle ne répond jamais deux fois pareil. "
     "Conséquence : 10 des 13 comportements déjà validés par les testeurs — refus de "
     "tricherie, refus hors-sujet, exactitude en prose — ne sont protégés par aucun test "
     "automatique.",
     "LLM-juge avec grille explicite (fournisseur, clé, budget), ou on assume de rester "
     "sans filet sur ce périmètre."),
    ("D9 — partiellement actée", "Lire les images des élèves ?",
     "La moitié honnête est livrée : l'agent dit clairement qu'il ne lit pas les captures "
     "et explique quoi faire à la place. L'upload réel avec OCR reste entier, et il n'est "
     "pas que technique — stockage d'images d'élèves mineurs, coût, vie privée.",
     "Fonctionnalité produit à planifier, ou hors périmètre assumé."),
    ("D11 — ouverte", "Quels chapitres manquent au corpus ?",
     "Trois cas se referment sur le même constat : l'agent refuse honnêtement un chapitre "
     "qu'il n'a pas — trigonométrie, trinômes, identités remarquables. Reste à savoir "
     "lesquels sont au programme officiel de la série visée : aucun référentiel n'est "
     "dans le dépôt, et l'affirmer sans source serait exactement ce qu'on interdit à "
     "l'agent.",
     "La liste des leçons à générer, et leur ordre de priorité."),
    ("Exploitation — à programmer", "Deux gestes sur l'environnement",
     "Réindexer le corpus : la normalisation des délimiteurs LaTeX s'applique à "
     "l'ingestion, donc pas à l'index déjà construit — il est protégé au moment de "
     "l'assemblage du prompt, mais une réindexation le remettrait au propre pour de bon. "
     "Surveiller le repli LLM : pendant les vérifications, Mistral a renvoyé des 503 et la "
     "chaîne est retombée sur le mock, qui produit une réponse générique — de l'extérieur, "
     "cela ressemble beaucoup à un agent amnésique.",
     "Hygiène : supprimer le compte de test qa31@tuteur.sn, et arrêter la stack Docker de "
     "démo restée démarrée."),
]

for reference, titre_d, corps, trancher in decisions:
    p = doc.add_paragraph(style="Heading 2")
    p.add_run(titre_d)
    p.paragraph_format.space_after = Pt(2)
    p = para(doc, reference, taille=8.5, couleur=PEN, espace_apres=4)
    p.runs[0].font.name = MONO
    para(doc, corps, espace_apres=4)
    riche(doc, [("À trancher : ", {"gras": True, "couleur": PEN}), (trancher, {})],
          espace_apres=12, gauche=0.4)

# --- 2. Les corrections, par cause racine ------------------------------------
h = doc.add_paragraph(style="Heading 1")
h.add_run("Les corrections, par cause racine")
filet(h, taille=12, position="top", couleur="101A28")

para(doc,
     "Le regroupement n'est pas cosmétique : c'est le principal enseignement du round. "
     "Presque aucun défaut rapporté n'était une dérive du modèle — la plupart étaient "
     "l'exécution fidèle d'une consigne ou d'un routage que nous avions écrits.",
     couleur=GRIS, espace_apres=10)

familles = [
    ("Des consignes qui se contredisaient",
     "La graduation socratique interdisait littéralement ce que l'élève demandait : "
     "« rappelle la règle sans l'appliquer » face à « donne-moi un exercice », « calcule », "
     "ou « reprends plus simplement ». La sur-socratisation n'était pas un excès de zèle du "
     "modèle, c'était la consigne.",
     "Escalades d'assemblage quand un résultat vérifié accompagne la demande ; branche "
     "d'entraînement dédiée qui va chercher un vrai énoncé du corpus ; niveau d'indice 2 "
     "imposé sur une demande de simplification ; illustration obligatoire après toute "
     "définition.",
     "9, 10, 11, 12, 13, 14, 31, 32, 39, 48"),
    ("Un routage d'intention trop étroit",
     "Tout ce qui n'était pas reconnu tombait en « exercice », le défaut : une salutation, "
     "une demande d'inventaire, une question sur l'utilité des maths, un « Expliques moi » "
     "mal accordé. Chaque raté produisait ensuite une réponse hors-sujet parfaitement "
     "logique.",
     "Intentions méta, salutation et entraînement ; tolérance aux variantes d'accord et "
     "d'infinitif ; réponses écrites par le code là où l'exigence porte sur l'exactitude "
     "(inventaire des chapitres, récapitulatif de session, capacités réelles de l'agent).",
     "2, 3, 4, 24, 26, 27, 35, 38, 41, 42, 43"),
    ("Savoir dire « je ne l'ai pas »",
     "Le seuil de pertinence mesurait l'accord des extraits remontés : il restait aveugle "
     "quand tout le top-k se trompait ensemble. Une question sur les dérivées remontait "
     "cinq extraits de calcul intégral, et l'agent y dérivait sans jamais signaler que la "
     "notion n'était pas couverte.",
     "Sous-classement des tours conceptuels et liaison au catalogue par titre, avec une "
     "borne stricte : dès que l'élève apporte son propre énoncé, aucun test de titre ne "
     "s'applique. Quand la notion manque — aucun extrait servi, aveu explicite, et la main "
     "rendue à l'élève au lieu d'une reprise forcée du cours.",
     "5, 28, 29, 30, 40, 44, 46"),
    ("Ne jamais annoncer un résultat non vérifié",
     "Le cas fondateur : « x³ − 3x » était tronqué au premier caractère non-ASCII, dérivé "
     "en « 1 », et le faux résultat présenté sous l'étiquette « vérifié par l'outil ». "
     "Même famille pour l'erreur de l'élève laissée passer et la démonstration longue "
     "invérifiable.",
     "Normalisation Unicode et extraction à double contrôle ; vérification symbolique "
     "étendue aux nombres complexes, aux études de fonction, aux affirmations de l'élève "
     "et désormais aux suites récurrentes (termes exacts, forme close, monotonie, borne, "
     "limite). Ce qui n'est pas démontré n'est pas dit.",
     "1, 6, 15, 17, 33, 45"),
    ("Ne rien inventer sur l'élève",
     "L'hallucination la plus gênante venait de nous : le bloc de documentation portait le "
     "nom de fichier « …_TS2S4.md », et le modèle en déduisait la série de l'élève. "
     "Ailleurs, il renvoyait à « la première partie » du cours au tout premier message.",
     "Le nom de fichier ne part plus au modèle ; la série déclarée par l'élève prime pour "
     "toute la session ; l'absence d'historique est dite explicitement plutôt que supposée "
     "évidente. L'étanchéité entre contexte admin et contexte élève est gelée par un test "
     "d'API.",
     "8, 16, 22, 34, 36"),
    ("L'élève avant la leçon",
     "Un signal de détresse ne doit jamais passer par le pipeline normal ; un découragement "
     "(« je suis nul en maths ») n'était détecté par rien ; et la même explication revenait "
     "une quatrième fois quand l'élève disait qu'elle ne passait pas.",
     "Disjoncteur de sécurité en tête de graphe, réponse déterministe, LLM non sollicité. "
     "Ouvertures de soutien écrites par le code, deux registres distincts, sans répétition "
     "dans une même session. Le blocage déclaré impose un changement d'angle, pas un cran "
     "d'indice de plus.",
     "7, 19, 20, 21"),
    ("Rendu, produit et données de test",
     "Le rendu LaTeX « à revoir » venait du corpus : les leçons écrivent leurs formules "
     "avec les délimiteurs \\( … \\) quand le format pivot est $ … $, et le modèle "
     "recopiait ce qu'on lui montrait. Deux lignes de suivi étaient inexploitables faute de "
     "réponse enregistrée.",
     "Normalisation des délimiteurs à l'ingestion et à l'assemblage du prompt ; suppression "
     "de conversation vérifiée de bout en bout et durcie côté interface ; lignes de suivi "
     "complétées par un rejeu réel plutôt que par une relance des testeurs.",
     "23, 25, 37, 47 — et 18, renvoyé au processus de contenu"),
]

for titre_f, cause, correctif, cas in familles:
    p = doc.add_paragraph(style="Heading 2")
    p.add_run(titre_f)
    p.paragraph_format.space_after = Pt(2)
    riche(doc, [("Cause racine — ", {"gras": True}), (cause, {"couleur": GRIS})],
          espace_apres=3)
    riche(doc, [("Correctif — ", {"gras": True}), (correctif, {})], espace_apres=3)
    riche(doc, [("Cas : ", {"taille": 9, "couleur": GRIS}),
                (cas, {"mono": True, "couleur": CLOS})], espace_apres=12)

# --- 3. La mémoire de conversation -------------------------------------------
h = doc.add_paragraph(style="Heading 1")
h.add_run("La mémoire de conversation")
filet(h, taille=12, position="top", couleur="101A28")

para(doc,
     "Traitée hors backlog, à la demande du porteur du projet. L'historique était bien "
     "persisté et rechargé — ce n'était pas là le problème. Le prompt ne portait qu'une "
     "fenêtre de six messages, soit trois échanges : au-delà, tout disparaissait. L'élève "
     "qui donnait son prénom au premier tour ne le retrouvait plus au cinquième, et "
     "l'exercice servi trois tours plus tôt n'existait plus.")
para(doc,
     "Un module de mémoire de session reconstruit désormais, par le code, ce que l'agent "
     "sait de la conversation en cours : le prénom donné par l'élève, les chapitres "
     "réellement travaillés, le dernier exercice servi. La fenêtre passe à douze messages, "
     "chacun tronqué pour ne pas gonfler le prompt. Le choix de ne rien faire résumer par "
     "le modèle est délibéré : une mémoire échantillonnée finit par inventer un contexte "
     "élève, ce que la règle non-négociable n°3 interdit.")
riche(doc, [
    ("Vérifié sur la stack réelle : après six messages, l'agent répond ", {}),
    ("« Tu t'appelles Awa, et nous travaillons ensemble sur les suites numériques »", {"italique": True}),
    (".", {}),
], espace_apres=12)

# --- 4. Inventaire complet ----------------------------------------------------
h = doc.add_paragraph(style="Heading 1")
h.add_run("Inventaire complet des 48 cas")
filet(h, taille=12, position="top", couleur="101A28")

cases = json.loads((DEPOT / "qa" / "qa_cases_all.json").read_text(encoding="utf-8"))
statuts = json.loads((DEPOT / "qa" / "qa_status.json").read_text(encoding="utf-8"))

#: Sujets reformulés pour la lecture en réunion (le JSON reste la source de vérité).
SUJETS = {
    2: "Retrieval hors-sujet sur « mon programme »",
    3: "Retrieval hors-sujet sur une demande d'astuces",
    5: "Chunks non pertinents servis faute de seuil",
    6: "Chapitre disponible non retrouvé (complexes)",
    10: "Calcul trivial non résolu (1−1)",
    17: "Réponse hors-sujet au lieu d'une étude de fonction",
    20: "Même contenu répété (3ᵉ explication)",
    22: "Réponse vide + soupçon de fuite du rôle admin",
    25: "Pas de mémoire de session / export",
    31: "Exercice demandé, jamais fourni",
    33: "Suite récurrente — démonstration à fiabiliser",
    36: "Référence à une « première partie » inexistante",
    43: "Relance de clôture déplacée",
    44: "Test non complété (trinômes)",
    47: "Rendu LaTeX d'une suite de valeurs",
    48: "Définition donnée sans exemple",
}
LIBELLE_STATUT = {
    "corrigé": ("corrigé", CLOS),
    "vérifié": ("vérifié", CLOS),
    "ne_sera_pas_corrigé": ("renvoyé au contenu", GRIS),
}

table = doc.add_table(rows=1, cols=5)
table.style = "Table Grid"
entetes = ("#", "Priorité", "Sujet", "Testeur", "Statut")
for i, texte in enumerate(entetes):
    cellule = table.rows[0].cells[i]
    p = cellule.paragraphs[0]
    r = p.add_run(texte)
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(8.5), True, GRIS, MONO
    fond(cellule, "EEF2F6")
table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))

for cas in cases:
    identifiant = cas["id"]
    statut = statuts[str(identifiant)]["status"]
    libelle, couleur = LIBELLE_STATUT[statut]
    ligne = table.add_row().cells

    r = ligne[0].paragraphs[0].add_run(str(identifiant))
    r.font.size, r.font.name, r.font.color.rgb = Pt(9), MONO, GRIS

    r = ligne[1].paragraphs[0].add_run(cas["priority"])
    r.font.size, r.font.color.rgb = Pt(9), GRIS

    r = ligne[2].paragraphs[0].add_run(SUJETS.get(identifiant, cas["subtheme"]))
    r.font.size = Pt(9)

    r = ligne[3].paragraphs[0].add_run(cas["tester"])
    r.font.size, r.font.color.rgb = Pt(9), GRIS

    r = ligne[4].paragraphs[0].add_run(libelle)
    r.font.size, r.font.name, r.font.color.rgb = Pt(8.5), MONO, couleur

    for cellule in ligne:
        cellule.paragraphs[0].paragraph_format.space_after = Pt(2)

for ligne in table.rows:
    for largeur, cellule in zip((Cm(1.1), Cm(2.0), Cm(8.4), Cm(3.0), Cm(2.5)), ligne.cells):
        cellule.width = largeur

# --- 5. Sur quoi repose cette clôture ----------------------------------------
h = doc.add_paragraph(style="Heading 1")
h.add_run("Sur quoi repose cette clôture")
filet(h, taille=12, position="top", couleur="101A28")

preuves = [
    ("Suite de tests",
     "1 235 tests verts, PostgreSQL réel inclus. Deux xfail assumés — les cas 18 et 23, "
     "dont le correctif vit hors du moteur pédagogique."),
    ("Non-régression",
     "Les 13 comportements validés par les testeurs sont rejoués à chaque exécution ; "
     "3 sont gelés par des assertions, 10 attendent la décision D2."),
    ("Vérification réelle",
     "Chaque correctif a été rejoué sur la stack Docker, avec le LLM de production et le "
     "prompt exact du testeur — pas seulement en test unitaire."),
    ("Traçabilité",
     "Cause racine, correctif et preuve consignés cas par cas dans qa/qa_status.json ; "
     "les arbitrages, avec ce qu'ils ont coûté à mettre en œuvre, dans qa/DECISIONS.md."),
]
for cle, valeur in preuves:
    riche(doc, [(f"{cle} — ", {"gras": True}), (valeur, {})], espace_apres=6)

SORTIE.parent.mkdir(parents=True, exist_ok=True)
maj_champs_a_l_ouverture(doc)
doc.save(SORTIE)
print(f"écrit : {SORTIE}")
