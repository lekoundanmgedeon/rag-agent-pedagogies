"""Adaptateur MCP interne pour les outils de calcul NURU.

Ce module crée un **registre d'outils unifié** qui expose les outils existants
(calculator, etude_fonction, complexe) derrière une interface standard inspirée
du protocole MCP (Model Context Protocol).

Avantages :
- L'agent ne dépend plus directement de chaque module outil ; il appelle
  ``tool_registry.invoke("nom_outil", {...})``.
- La migration vers un vrai serveur MCP (lib ``mcp`` ou FastMCP) sera triviale :
  il suffira de remplacer ``ToolRegistry.invoke`` par un appel HTTP/stdio.
- Chaque outil est découvrable : ``tool_registry.list_tools()`` renvoie les
  schémas compatibles avec la spec MCP (name, description, inputSchema).

**Pas de dépendance externe.** Tout repose sur les modules Python existants.

# ============================================================================
# ÉVOLUTION PRÉVUE — Couche d'abstraction MCP complète
# ============================================================================
#
# La classe ToolRegistry est conçue pour évoluer progressivement vers une
# couche d'abstraction entièrement compatible avec le protocole MCP officiel
# (Model Context Protocol — spec Anthropic / open standard).
#
# Étapes de migration planifiées :
#
#   1. (Actuel)  ToolRegistry.invoke() appelle directement les fonctions Python.
#
#   2. (Court terme) ToolRegistry devient une interface abstraite (ABC) avec
#      deux implémentations :
#        - LocalToolRegistry  : appels Python directs (état actuel)
#        - McpToolRegistry    : appels via stdio / HTTP vers un serveur MCP
#
#   3. (Long terme) Exposer un vrai serveur MCP (FastMCP ou mcp-python-sdk)
#      qui encapsule les mêmes handlers. L'agent restera inchangé :
#      seul le backend de ToolRegistry change.
#
# Principe directeur : l'interface ToolRegistry ne doit JAMAIS changer quand
# on passe d'une implémentation à l'autre. C'est la seule garantie que le
# graphe LangGraph n'aura pas à être modifié lors de la migration MCP.
# ============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass(frozen=True)
class ToolSchema:
    """Métadonnées d'un outil, compatibles avec le schema MCP."""
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema de l'input


@dataclass
class ToolResult:
    """Résultat normalisé d'un appel d'outil."""
    tool_name: str
    success: bool
    content: Any           # Résultat principal (dict, str, list…)
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata,
        }


# Type d'un handler d'outil : async (params: dict) -> Any
ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


class ToolRegistry:
    """Registre centralisé des outils de l'agent.

    Tous les outils sont enregistrés ici au démarrage. Le graphe LangGraph
    les appelle via ``invoke(name, params)`` sans connaître leurs implémentations.
    """

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSchema, ToolHandler]] = {}

    def register(self, schema: ToolSchema, handler: ToolHandler) -> None:
        """Enregistre un outil dans le registre."""
        self._tools[schema.name] = (schema, handler)

    def list_tools(self) -> list[ToolSchema]:
        """Renvoie les schémas de tous les outils enregistrés (découvrabilité MCP)."""
        return [schema for schema, _ in self._tools.values()]

    async def invoke(self, tool_name: str, params: dict[str, Any]) -> ToolResult:
        """Invoque un outil par son nom avec les paramètres donnés."""
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                content=None,
                error=f"Outil inconnu : '{tool_name}'. Outils disponibles : {list(self._tools)}",
            )

        schema, handler = self._tools[tool_name]
        try:
            result = await handler(params)
            return ToolResult(tool_name=tool_name, success=True, content=result)
        except Exception as exc:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                content=None,
                error=f"Erreur lors de l'exécution de '{tool_name}' : {exc}",
            )
