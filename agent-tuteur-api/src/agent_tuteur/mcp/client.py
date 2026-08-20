"""MCP Client — Interface pour brancher un serveur MCP au ToolRegistry interne.

Ce module permet de se connecter à un serveur MCP standard (via stdio) et 
d'enregistrer dynamiquement ses outils dans le `ToolRegistry`. Les agents
LangGraph (Agent Cours, Validation) pourront alors utiliser ces outils de
manière transparente.
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

from agent_tuteur.mcp import ToolRegistry, ToolSchema, ToolHandler


class McpClient:
    """Client MCP qui gère la connexion à un serveur MCP (stdio) et 
    l'enregistrement de ses outils dans le ToolRegistry local.
    """

    def __init__(self, command: str, args: list[str]) -> None:
        """Initialise le client avec la commande pour lancer le serveur MCP.
        
        Exemple : McpClient(command="python", args=["-m", "agent_tuteur.mcp_servers.math_server"])
        """
        self.server_params = StdioServerParameters(command=command, args=args)
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def connect(self) -> None:
        """Démarre le processus du serveur et établit la session MCP."""
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
        read, write = stdio_transport
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def disconnect(self) -> None:
        """Ferme la connexion et arrête proprement le processus du serveur."""
        await self._exit_stack.aclose()
        self.session = None

    async def register_tools(self, registry: ToolRegistry) -> None:
        """Découvre les outils du serveur MCP et les enregistre dans le ToolRegistry.
        
        Pour chaque outil renvoyé par le serveur, on crée un ToolSchema et un 
        ToolHandler proxy qui relaye les appels vers le serveur distant.
        """
        if not self.session:
            raise RuntimeError("Le client MCP n'est pas connecté. Appelez connect() d'abord.")

        tools_response = await self.session.list_tools()
        
        for tool in tools_response.tools:
            # 1. Création du schéma d'outil local basé sur les métadonnées MCP
            schema = ToolSchema(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema or {},
            )
            
            # 2. Création du proxy asynchrone (fermeture sur le nom de l'outil)
            def create_handler(tool_name: str) -> ToolHandler:
                async def _proxy_handler(params: dict[str, Any]) -> Any:
                    if not self.session:
                        raise RuntimeError(f"Client MCP déconnecté lors de l'appel à '{tool_name}'")
                    
                    result: CallToolResult = await self.session.call_tool(tool_name, arguments=params)
                    
                    if result.isError:
                        erreur_texte = "\n".join(
                            c.text for c in result.content if hasattr(c, "text")
                        )
                        raise RuntimeError(f"Erreur MCP de '{tool_name}' : {erreur_texte}")
                    
                    # Normalisation du résultat MCP en chaîne de caractères
                    return "\n".join(
                        c.text for c in result.content if hasattr(c, "text")
                    )
                return _proxy_handler
                
            # 3. Enregistrement dans le registre central
            registry.register(schema, create_handler(tool.name))
