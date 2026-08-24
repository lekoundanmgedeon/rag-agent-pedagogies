"""Enregistrement des outils NURU dans le registre MCP interne.

Ce fichier est le **point d'entrée unique** pour tous les outils du système.
Il enregistre chaque outil avec son schéma JSON et son handler async, en
wrappant les fonctions synchrones existantes via ``asyncio.to_thread``.

Principe : les outils Python existants (calculator.py, etude_fonction.py,
complexe.py) sont conservés **sans modification**. Ce module ajoute uniquement
une couche adaptateur qui les rend invocables via le registre MCP.
"""

from __future__ import annotations

import asyncio
from typing import Any

from agent_tuteur.mcp import ToolRegistry, ToolResult, ToolSchema
from agent_tuteur.tools.calculator import compute, CalculationResult
from agent_tuteur.tools.etude_fonction import etudier_la_demande, etudier
from agent_tuteur.tools.complexe import analyser_la_demande, analyser_complexe


def build_tool_registry() -> ToolRegistry:
    """Construit et retourne le registre MCP avec tous les outils enregistrés."""
    registry = ToolRegistry()

    # ----------------------------------------------------------------- calculatrice
    async def _handle_compute(params: dict[str, Any]) -> dict:
        query = params.get("query", "")
        result: CalculationResult = await asyncio.to_thread(compute, query)
        return {
            "expression": result.expression,
            "result": str(result.result) if result.result is not None else None,
            "operation": result.operation,
            "error": result.error,
        }

    registry.register(
        ToolSchema(
            name="compute",
            description=(
                "Calcule une expression mathématique (dérivée, intégrale, résolution "
                "d'équation, simplification). Utiliser quand l'élève demande un calcul "
                "exact. Renvoie l'expression normalisée et le résultat SymPy."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La question ou l'expression mathématique à calculer (texte naturel ou expression).",
                    }
                },
                "required": ["query"],
            },
        ),
        handler=_handle_compute,
    )

    # ----------------------------------------------------------------- étude de fonction
    async def _handle_etude(params: dict[str, Any]) -> dict:
        query = params.get("query", "")
        etude = await asyncio.to_thread(etudier_la_demande, query)
        if etude is None:
            return {"success": False, "error": "Aucune expression de fonction détectée dans la question."}
        if not etude.est_exploitable():
            return {"success": False, "error": "La fonction n'a pas pu être étudiée (expression invalide)."}
        return {
            "success": True,
            "expression": etude.expression,
            "domaine": etude.domaine,
            "limites": etude.limites,
            "derivee": etude.derivee,
            "variations": etude.variations,
            "texte": etude.texte_mise_en_page() if hasattr(etude, "texte_mise_en_page") else str(etude),
        }

    registry.register(
        ToolSchema(
            name="etudier_fonction",
            description=(
                "Réalise l'étude complète d'une fonction (domaine de définition, "
                "dérivée, variations, limites). À utiliser pour un cours ou un exercice "
                "portant sur l'étude d'une fonction mathématique."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La question ou l'expression de la fonction à étudier.",
                    }
                },
                "required": ["query"],
            },
        ),
        handler=_handle_etude,
    )

    # ----------------------------------------------------------------- nombres complexes
    async def _handle_complexe(params: dict[str, Any]) -> dict:
        query = params.get("query", "")
        analyse = await asyncio.to_thread(analyser_la_demande, query)
        if analyse is None:
            return {"success": False, "error": "Aucune expression complexe détectée dans la question."}
        return {
            "success": True,
            "module": str(analyse.module) if analyse.module is not None else None,
            "argument": str(analyse.argument) if analyse.argument is not None else None,
            "partie_reelle": str(analyse.partie_reelle) if analyse.partie_reelle is not None else None,
            "partie_imaginaire": str(analyse.partie_imaginaire) if analyse.partie_imaginaire is not None else None,
            "forme_algebrique": analyse.forme_algebrique,
            "forme_trigonometrique": analyse.forme_trigonometrique,
        }

    registry.register(
        ToolSchema(
            name="analyser_complexe",
            description=(
                "Analyse un nombre complexe : module, argument, parties réelle et "
                "imaginaire, formes algébrique et trigonométrique. À utiliser quand "
                "l'élève travaille sur les nombres complexes."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La question ou l'expression du nombre complexe à analyser.",
                    }
                },
                "required": ["query"],
            },
        ),
        handler=_handle_complexe,
    )

    return registry
