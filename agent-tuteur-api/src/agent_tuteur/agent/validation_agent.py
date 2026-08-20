"""Agent Validation — service commun de contrôle du contenu généré.

Branché après ``compose_response`` dans le graphe LangGraph, il contrôle les
réponses produites par :
- l'Agent Cours (``llm_cours``, GPT-5.5)       quand ``intent == "cours"``
- l'Agent Exercices/Quiz (``llm_exercice``, Mistral)  quand ``intent`` est
  ``"exercice"`` ou ``"quiz"``

**Deux couches de contrôle, dans cet ordre :**

1. **Déterministe** (sans LLM, instantané) :
   - Contrôles SymPy : fidélité au calcul exact, cohérence des expressions
   - Contrôle de vocabulaire hors-programme
   - Contrôle de cohérence des résultats d'étude de fonction

2. **LLM-as-a-Judge** (appel LLM léger, uniquement si la couche 1 passe) :
   - Exactitude pédagogique
   - Cohérence avec la question de l'élève
   - Conformité au niveau Terminale S1 / programme sénégalais
   - Fidélité aux sources RAG fournies
   - Clarté de l'explication
   - Absence d'hallucination

**Verdicts possibles :**

- ``PASS``   — réponse validée, prête à être envoyée à l'élève
- ``REPAIR`` — erreur corrigeable, régénération avec feedback ciblé
- ``REVIEW`` — cas ambigu, mise en attente pour revue humaine
- ``FAIL``   — rejet définitif (contenu dangereux ou qualité trop faible)

**Ce module ne modifie aucun composant existant.** Il est appelé depuis
``graph._n_verify`` à la place de l'appel direct à ``verify.py``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum

from agent_tuteur.agent.llm.base import BaseLLM
from agent_tuteur.agent.verify import (
    RapportVerification,
    verifier_coherence_mathematique,
    verifier_coherence_etude_fonction,
    verifier_coherence_exercice,
)
from agent_tuteur.observability import get_logger, log_event

_logger = get_logger("agent_tuteur.agent.validation_agent")


# ---------------------------------------------------------------------------
# Types de sortie structurée
# ---------------------------------------------------------------------------


class Verdict(str, Enum):
    """Décision finale de l'Agent Validation."""

    PASS = "PASS"
    REPAIR = "REPAIR"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    """Résultat complet de la validation d'une réponse générée.

    Tous les champs sont présents quelle que soit la décision — les
    appelants (``graph._n_verify``, les tests) ne font jamais de ``get``
    défensif sur un champ optionnel.
    """

    verdict: Verdict
    """Décision globale : PASS / REPAIR / REVIEW / FAIL."""

    score: float
    """Score de qualité global, entre 0.0 (rejet) et 1.0 (parfait)."""

    erreurs: list[str] = field(default_factory=list)
    """Liste des problèmes détectés (couche déterministe + juge LLM)."""

    criteres_valides: list[str] = field(default_factory=list)
    """Critères explicitement satisfaits (pour la traçabilité pédagogique)."""

    recommandations: list[str] = field(default_factory=list)
    """Instructions concrètes de correction, injectées dans le prompt de repair."""

    explication: str = ""
    """Explication lisible par un humain (opérateur, log d'audit)."""

    couche_deterministe: bool = True
    """La couche déterministe a-t-elle été exécutée ? (toujours vrai)"""

    couche_llm_judge: bool = False
    """La couche LLM-as-a-Judge a-t-elle été exécutée ?"""

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "erreurs": self.erreurs,
            "criteres_valides": self.criteres_valides,
            "recommandations": self.recommandations,
            "explication": self.explication,
            "couche_deterministe": self.couche_deterministe,
            "couche_llm_judge": self.couche_llm_judge,
        }

    @property
    def est_valide(self) -> bool:
        """Rétrocompatibilité avec le code existant qui vérifie ``verification["valide"]``."""
        return self.verdict == Verdict.PASS

    @property
    def problemes(self) -> list[str]:
        """Rétrocompatibilité avec ``RapportVerification.problemes``."""
        return self.erreurs

    def feedback_pour_repair(self) -> str:
        """Texte injecté dans le prompt de régénération (``validation_feedback``)."""
        lignes = ["Erreurs détectées dans ta réponse précédente :"]
        for e in self.erreurs:
            lignes.append(f"  • {e}")
        if self.recommandations:
            lignes.append("\nCorrections attendues :")
            for r in self.recommandations:
                lignes.append(f"  → {r}")
        return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Prompt du juge LLM
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = (
    "Tu es un expert en pédagogie mathématique pour le programme scolaire sénégalais "
    "(Terminale S1 et niveaux apparentés). Tu évalues objectivement la qualité des "
    "réponses d'un tuteur IA. Tu réponds UNIQUEMENT en JSON valide, sans markdown."
)

_JUDGE_PROMPT = """\
CONTEXTE
========
Question de l'élève : {question}
Intention détectée  : {intent}
Niveau d'indice autorisé (0=reformuler, 4=solution complète) : {hint_level}

SOURCES RAG UTILISÉES
=====================
{rag_sources}

RÉPONSE DU TUTEUR À ÉVALUER
============================
{answer}

CRITÈRES D'ÉVALUATION
======================
Évalue chaque critère avec true/false et une courte justification.

1. exactitude_pedagogique   : La réponse est-elle mathématiquement correcte et pédagogiquement juste ?
2. coherence_question       : La réponse répond-elle bien à la question posée ?
3. conformite_programme     : La réponse respecte-t-elle le niveau Terminale S1 / programme sénégalais
                              (pas de notions universitaires hors-programme) ?
4. fidelite_rag             : La réponse s'appuie-t-elle sur les sources fournies sans inventer
                              des faits absents des sources ?
5. clarte_explication       : L'explication est-elle claire et adaptée au niveau de l'élève ?
6. absence_hallucination    : La réponse ne contient-elle pas de formules, théorèmes ou résultats
                              non vérifiables ou inventés ?
7. respect_niveau_indice    : Si intent="exercice" et hint_level < 4, le tuteur guide-t-il
                              plutôt que de donner la solution complète ?

RÈGLE DE VERDICT
================
- Si tous les critères sont true → "PASS"
- Si 1–2 critères mineurs sont false (clarte, coherence_question) → "REPAIR"
- Si exactitude_pedagogique OU absence_hallucination est false → "REPAIR" (grave)
- Si respect_niveau_indice est false → "REPAIR" (règle pédagogique violée)
- Si fidelite_rag est false ET aucune source n'était fournie → "REVIEW" (ambigu)
- Si conformite_programme est false ET la notion est clairement hors-programme → "FAIL"
- En cas de doute sur la gravité → "REVIEW"

FORMAT DE RÉPONSE (JSON strict, sans texte autour)
===================================================
{{
  "criteres": {{
    "exactitude_pedagogique":  {{"ok": true/false, "note": "..."}},
    "coherence_question":      {{"ok": true/false, "note": "..."}},
    "conformite_programme":    {{"ok": true/false, "note": "..."}},
    "fidelite_rag":            {{"ok": true/false, "note": "..."}},
    "clarte_explication":      {{"ok": true/false, "note": "..."}},
    "absence_hallucination":   {{"ok": true/false, "note": "..."}},
    "respect_niveau_indice":   {{"ok": true/false, "note": "..."}}
  }},
  "verdict": "PASS"|"REPAIR"|"REVIEW"|"FAIL",
  "explication": "résumé court du verdict",
  "recommandations": ["instruction 1", "instruction 2"]
}}
"""

# Critères dont l'échec entraîne directement FAIL (hors-programme confirmé)
_CRITERES_FAIL = frozenset({"conformite_programme"})

# Critères dont l'échec est grave (REPAIR prioritaire)
_CRITERES_GRAVES = frozenset({"exactitude_pedagogique", "absence_hallucination", "respect_niveau_indice"})

# Critères dont l'échec peut justifier REVIEW (ambiguïté)
_CRITERES_REVIEW = frozenset({"fidelite_rag"})


# ---------------------------------------------------------------------------
# Agent Validation
# ---------------------------------------------------------------------------


class ValidationAgent:
    """Service commun de contrôle qualité pour les agents cours et exercices.

    Usage dans ``graph._n_verify`` ::

        validator = ValidationAgent(llm_juge)
        result = await validator.validate(
            answer=draft_answer,
            question=state["question"],
            intent=state.get("intent", "exercice"),
            hint_level=state.get("hint_level", 0),
            rag_sources=state.get("retrieved", []),
            tool_result_brut=state.get("tool_result_brut"),
            competence=state.get("trace", {}).get("competence"),
            etude_fonction=state.get("etude_fonction"),
            repair_attempts=state.get("repair_attempts", 0),
        )

    Le ``ValidationAgent`` est sans état propre : une seule instance peut être
    réutilisée pour toutes les requêtes concurrentes (idem ``TutorAgent``).
    """

    #: Seuil de score en dessous duquel on passe directement en FAIL
    #: sans tenter de repair (réponse trop dégradée pour être réparée).
    SCORE_FAIL_THRESHOLD: float = 0.25

    #: Seuil de score en dessous duquel REVIEW est préféré à REPAIR
    #: (cas ambigu où un humain doit trancher).
    SCORE_REVIEW_THRESHOLD: float = 0.45

    def __init__(self, llm_juge: BaseLLM) -> None:
        """
        :param llm_juge: LLM utilisé pour le juge pédagogique. En pratique,
            ``llm_cours`` (GPT-5.5) est recommandé pour sa capacité d'analyse,
            mais ``llm_exercice`` (Mistral) fonctionne en fallback.
        """
        self._llm = llm_juge

    # ------------------------------------------------------------------
    # Point d'entrée public
    # ------------------------------------------------------------------

    async def validate(
        self,
        *,
        answer: str,
        question: str,
        intent: str,
        hint_level: int = 0,
        rag_sources: list | None = None,
        tool_result_brut: str | None = None,
        competence: str | None = None,
        etude_fonction: dict | None = None,
        repair_attempts: int = 0,
        trace_id: str | None = None,
    ) -> ValidationResult:
        """Exécute les deux couches de contrôle et retourne un ``ValidationResult``.

        :param answer: La réponse brute générée par le LLM (``draft_answer``).
        :param question: La question originale de l'élève.
        :param intent: ``"cours"``, ``"exercice"`` ou ``"quiz"``.
        :param hint_level: Niveau d'indice autorisé (0–4), pertinent en mode exercice.
        :param rag_sources: Extraits RAG utilisés (``list[ScoredChunk]``).
        :param tool_result_brut: Résultat exact calculé par SymPy (si disponible).
        :param competence: Compétence traitée (pour filtrer les termes hors-programme).
        :param etude_fonction: Résultat d'étude de fonction SymPy (si disponible).
        :param repair_attempts: Nombre de tentatives déjà effectuées (protège des boucles).
        :param trace_id: Identifiant de corrélation pour les logs.
        """
        # --- Couche 1 : contrôles déterministes ----------------------------
        rapport_det = self._run_deterministic(
            answer=answer,
            competence=competence,
            tool_result_brut=tool_result_brut,
            etude_fonction=etude_fonction,
            intent=intent,
        )

        criteres_valides: list[str] = []
        erreurs: list[str] = list(rapport_det.problemes)
        recommandations: list[str] = []

        if rapport_det.est_valide:
            criteres_valides.append("cohérence_mathématique_déterministe")
        else:
            recommandations.extend(self._recommandations_deterministes(rapport_det))

        # --- Couche 2 : LLM-as-a-Judge -------------------------------------
        judge_result: dict | None = None
        llm_judge_ran = False

        try:
            judge_result = await self._run_llm_judge(
                answer=answer,
                question=question,
                intent=intent,
                hint_level=hint_level,
                rag_sources=rag_sources or [],
            )
            llm_judge_ran = True
        except Exception as exc:  # noqa: BLE001
            # Le juge ne doit jamais bloquer la réponse à l'élève.
            log_event(
                _logger, "validation:judge_error",
                log_level=logging.WARNING,
                trace_id=trace_id,
                error=str(exc),
            )

        # --- Fusion des résultats ------------------------------------------
        if judge_result is not None:
            j_erreurs, j_valides, j_reco = self._parse_judge_result(judge_result)
            erreurs.extend(j_erreurs)
            criteres_valides.extend(j_valides)
            recommandations.extend(j_reco)

        # --- Calcul du score et du verdict ----------------------------------
        result = self._compute_verdict(
            erreurs=erreurs,
            criteres_valides=criteres_valides,
            recommandations=recommandations,
            judge_result=judge_result,
            rapport_det=rapport_det,
            repair_attempts=repair_attempts,
            llm_judge_ran=llm_judge_ran,
            trace_id=trace_id,
        )

        log_event(
            _logger, "validation:result",
            trace_id=trace_id,
            verdict=result.verdict.value,
            score=result.score,
            n_erreurs=len(result.erreurs),
            repair_attempts=repair_attempts,
            intent=intent,
        )
        return result

    # ------------------------------------------------------------------
    # Couche 1 : déterministe
    # ------------------------------------------------------------------

    def _run_deterministic(
        self,
        *,
        answer: str,
        competence: str | None,
        tool_result_brut: str | None,
        etude_fonction: dict | None,
        intent: str,
    ) -> RapportVerification:
        """Exécute tous les contrôles déterministes et agrège les problèmes."""
        problemes: list[str] = []

        # 1a. Cohérence mathématique (vocabulaire + fidélité calcul SymPy)
        r1 = verifier_coherence_mathematique(
            answer,
            competence=competence,
            resultat_calcule=tool_result_brut,
        )
        problemes.extend(r1.problemes)

        # 1b. Cohérence de l'étude de fonction SymPy
        if etude_fonction is not None:
            r2 = verifier_coherence_etude_fonction(answer, etude_fonction)
            problemes.extend(r2.problemes)

        # 1c. Contrôle exercice : la solution ne doit pas être donnée
        #     si hint_level < 4 (vérifié ici par détection heuristique rapide,
        #     le juge LLM est plus précis mais plus coûteux).
        if intent == "exercice":
            r3 = verifier_coherence_exercice(answer)
            problemes.extend(r3.problemes)

        return RapportVerification(problemes=problemes)

    @staticmethod
    def _recommandations_deterministes(rapport: RapportVerification) -> list[str]:
        """Traduit les problèmes déterministes en instructions de correction."""
        reco = []
        for p in rapport.problemes:
            if "hors-programme" in p:
                reco.append(
                    "Reste dans le programme scolaire sénégalais (Terminale S1). "
                    "Évite les notions d'analyse à plusieurs variables (dérivées partielles, gradient)."
                )
            elif "n'apparaît pas" in p:
                reco.append(
                    "Le résultat du calcul exact doit apparaître tel quel dans ta réponse. "
                    "Ne refais pas le calcul toi-même."
                )
            elif "étude de fonction" in p.lower():
                reco.append(
                    "Les résultats de l'étude de fonction (domaine, dérivée, limites, variations) "
                    "doivent correspondre exactement aux valeurs calculées par SymPy."
                )
            else:
                reco.append(f"Corrige : {p}")
        return reco

    # ------------------------------------------------------------------
    # Couche 2 : LLM-as-a-Judge
    # ------------------------------------------------------------------

    async def _run_llm_judge(
        self,
        *,
        answer: str,
        question: str,
        intent: str,
        hint_level: int,
        rag_sources: list,
    ) -> dict:
        """Appelle le LLM juge et retourne le résultat parsé.

        Lève une exception si le LLM échoue ou si le JSON est invalide —
        l'appelant (``validate``) gère le fallback silencieux.
        """
        # On ne juge pas les tours de sécurité / salutation / meta
        if intent not in ("cours", "exercice", "quiz"):
            return {
                "criteres": {},
                "verdict": "PASS",
                "explication": f"Verdict PASS automatique pour l'intention « {intent} ».",
                "recommandations": [],
            }

        rag_text = self._format_rag_sources(rag_sources)

        prompt = _JUDGE_PROMPT.format(
            question=question,
            intent=intent,
            hint_level=hint_level,
            rag_sources=rag_text if rag_text else "(aucune source RAG disponible pour ce tour)",
            answer=answer,
        )

        raw = await self._llm.generate(prompt, system=_JUDGE_SYSTEM)

        # Nettoyage des balises markdown que certains modèles ajoutent malgré
        # la consigne (Mistral notamment).
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        return json.loads(raw.strip())

    @staticmethod
    def _format_rag_sources(rag_sources: list) -> str:
        """Formate les sources RAG pour le prompt du juge."""
        if not rag_sources:
            return ""
        lignes = []
        for i, sc in enumerate(rag_sources[:5], 1):  # Max 5 sources pour le juge
            # Rétrocompat : sc peut être un ScoredChunk ou un dict (tests)
            if hasattr(sc, "chunk"):
                texte = (sc.chunk.text or "")[:300]
                chapitre = getattr(sc.chunk.metadata, "chapitre", "") or ""
                lignes.append(f"[Source {i} — {chapitre}]\n{texte}")
            elif isinstance(sc, dict):
                texte = str(sc.get("text", sc.get("content", "")))[:300]
                lignes.append(f"[Source {i}]\n{texte}")
        return "\n\n".join(lignes)

    # ------------------------------------------------------------------
    # Parsing du résultat du juge
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_judge_result(
        judge: dict,
    ) -> tuple[list[str], list[str], list[str]]:
        """Extrait erreurs, critères valides et recommandations du résultat du juge."""
        erreurs: list[str] = []
        valides: list[str] = []
        recommandations: list[str] = list(judge.get("recommandations") or [])

        criteres: dict = judge.get("criteres") or {}
        for nom, detail in criteres.items():
            if not isinstance(detail, dict):
                continue
            if detail.get("ok") is True:
                valides.append(nom)
            elif detail.get("ok") is False:
                note = detail.get("note", "")
                erreurs.append(f"[Juge] {nom} : {note}" if note else f"[Juge] {nom} non validé")

        return erreurs, valides, recommandations

    # ------------------------------------------------------------------
    # Calcul du verdict final
    # ------------------------------------------------------------------

    def _compute_verdict(
        self,
        *,
        erreurs: list[str],
        criteres_valides: list[str],
        recommandations: list[str],
        judge_result: dict | None,
        rapport_det: RapportVerification,
        repair_attempts: int,
        llm_judge_ran: bool,
        trace_id: str | None,
    ) -> ValidationResult:
        """Fusionne les deux couches et produit le ``ValidationResult`` final."""
        n_total_criteres = len(criteres_valides) + len(erreurs)
        if n_total_criteres == 0:
            # Aucun critère évalué (ex. intention non jugeable) → PASS par défaut
            return ValidationResult(
                verdict=Verdict.PASS,
                score=1.0,
                criteres_valides=criteres_valides,
                erreurs=[],
                recommandations=[],
                explication="Aucun critère de validation applicable pour ce tour.",
                couche_deterministe=True,
                couche_llm_judge=llm_judge_ran,
            )

        score = len(criteres_valides) / n_total_criteres

        # --- Verdict du juge LLM (si disponible) --------------------------
        judge_verdict_str: str | None = None
        explication = ""
        if judge_result is not None:
            judge_verdict_str = judge_result.get("verdict", "").upper()
            explication = judge_result.get("explication", "")

        # --- Règles de verdict (priorité décroissante) --------------------

        # Règle 1 : Pas d'erreur du tout → PASS
        if not erreurs:
            return ValidationResult(
                verdict=Verdict.PASS,
                score=1.0,
                criteres_valides=criteres_valides,
                erreurs=[],
                recommandations=[],
                explication=explication or "Tous les critères sont satisfaits.",
                couche_deterministe=True,
                couche_llm_judge=llm_judge_ran,
            )

        # Règle 2 : Score trop bas pour toute tentative de repair → FAIL
        if score < self.SCORE_FAIL_THRESHOLD:
            return ValidationResult(
                verdict=Verdict.FAIL,
                score=score,
                erreurs=erreurs,
                criteres_valides=criteres_valides,
                recommandations=recommandations,
                explication=explication or f"Score trop bas ({score:.0%}) pour réparation.",
                couche_deterministe=True,
                couche_llm_judge=llm_judge_ran,
            )

        # Règle 3 : Le juge dit FAIL explicitement
        if judge_verdict_str == Verdict.FAIL.value:
            return ValidationResult(
                verdict=Verdict.FAIL,
                score=score,
                erreurs=erreurs,
                criteres_valides=criteres_valides,
                recommandations=recommandations,
                explication=explication,
                couche_deterministe=True,
                couche_llm_judge=llm_judge_ran,
            )

        # Règle 4 : Le juge dit REVIEW ou score ambigu
        is_review = (
            judge_verdict_str == Verdict.REVIEW.value
            or (
                not llm_judge_ran  # juge indisponible : ambigu
                and not rapport_det.est_valide  # mais la couche det a trouvé des problèmes
                and score >= self.SCORE_REVIEW_THRESHOLD
            )
        )
        if is_review:
            return ValidationResult(
                verdict=Verdict.REVIEW,
                score=score,
                erreurs=erreurs,
                criteres_valides=criteres_valides,
                recommandations=recommandations,
                explication=explication or "Cas ambigu nécessitant une revue humaine.",
                couche_deterministe=True,
                couche_llm_judge=llm_judge_ran,
            )

        # Règle 5 : Erreurs → REPAIR (cas normal, corrigeable)
        return ValidationResult(
            verdict=Verdict.REPAIR,
            score=score,
            erreurs=erreurs,
            criteres_valides=criteres_valides,
            recommandations=recommandations,
            explication=explication or f"{len(erreurs)} erreur(s) détectée(s), régénération demandée.",
            couche_deterministe=True,
            couche_llm_judge=llm_judge_ran,
        )
