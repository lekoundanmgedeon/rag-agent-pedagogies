"""MCP RAG Server (Priorité 2) — Serveur MCP dédié au corpus pédagogique NURU.

Permet à l'Agent Validation (ou tout autre agent) d'accéder aux capacités
RAG via des outils standardisés. Ce serveur se branche sur l'infrastructure
existante (embeddings, vector store Qdrant/Memory).
"""

from __future__ import annotations

import json
from mcp.server.fastmcp import FastMCP

from agent_tuteur.config.settings import get_settings
from agent_tuteur.factory import build_rag_stack, build_llm_cours
from agent_tuteur.vectorstore.retriever import HybridRetriever
from agent_tuteur.agent.verify import verifier_pedagogie

# Initialisation du serveur
mcp = FastMCP("nuru-rag-mcp")

# Variables globales paresseuses (initialisées au premier appel pour éviter
# de ralentir ou planter l'import de ce module).
_rag_stack = None
_llm = None

def _get_retriever() -> HybridRetriever:
    global _rag_stack
    if _rag_stack is None:
        settings = get_settings()
        _rag_stack = build_rag_stack(settings)
    return _rag_stack.retriever

def _get_llm():
    global _llm
    if _llm is None:
        settings = get_settings()
        _llm = build_llm_cours(settings)  # LLM de validation (GPT-5.5)
    return _llm

@mcp.tool()
def search_curriculum(query: str) -> str:
    """Recherche une notion mathématique dans le programme scolaire officiel.
    
    Args:
        query: La notion à chercher (ex: "nombres complexes", "dérivée").
    """
    retriever = _get_retriever()
    # On force la recherche sur les documents de type 'programme'
    # si le corpus est structuré ainsi, sinon on cherche dans le cours.
    # Pour l'instant, on cherche de manière générale mais on ajoute le contexte.
    resultats = retriever.retrieve(query + " programme compétences attendues", top_k=3)
    if not resultats.tous():
        return "Aucune notion trouvée dans le corpus pour : " + query
    
    reponse = []
    for sc in resultats.tous():
        reponse.append(f"[Chapitre: {sc.chunk.metadata.chapitre}]\n{sc.chunk.text}")
    return "\n\n---\n\n".join(reponse)

@mcp.tool()
def search_knowledge(query: str, top_k: int = 5) -> str:
    """Recherche des passages pertinents dans le corpus pédagogique NURU (cours, exercices).
    
    Args:
        query: La question ou le concept à chercher.
        top_k: Nombre maximum d'extraits à retourner.
    """
    retriever = _get_retriever()
    resultats = retriever.retrieve(query, top_k=top_k)
    
    if not resultats.tous():
        return "Aucun résultat trouvé dans le corpus NURU."
        
    reponse = []
    for i, sc in enumerate(resultats.tous(), 1):
        type_doc = sc.chunk.metadata.type_document
        chapitre = sc.chunk.metadata.chapitre
        reponse.append(f"Source {i} ({type_doc} - {chapitre}):\n{sc.chunk.text}")
        
    return "\n\n".join(reponse)

@mcp.tool()
def get_source(chapitre: str) -> str:
    """Récupère l'intégralité des extraits associés à un chapitre précis.
    
    Args:
        chapitre: Nom exact ou partiel du chapitre (ex: "Nombres complexes").
    """
    retriever = _get_retriever()
    # Le retriever possède chunks_du_chapitre
    chunks = retriever.chunks_du_chapitre(chapitre)
    
    if not chunks:
        return f"Aucune source trouvée pour le chapitre : {chapitre}"
        
    reponse = []
    for chunk in chunks:
        reponse.append(f"[{chunk.metadata.type_chunk}] {chunk.text}")
        
    return "\n\n".join(reponse)

@mcp.tool()
async def check_grounding(affirmation: str, sources_texte: str) -> str:
    """Vérifie qu'une affirmation est supportée par les sources (absence d'hallucination).
    
    Args:
        affirmation: La phrase ou l'explication à vérifier.
        sources_texte: Le texte des sources de référence à utiliser.
    """
    llm = _get_llm()
    prompt = f"""
Agis comme un vérificateur de faits stricts.
On te donne un ensemble de sources pédagogiques et une affirmation.
Ta tâche est de déterminer si l'affirmation est ENTIÈREMENT SUPPORTÉE par les sources.

SOURCES:
{sources_texte}

AFFIRMATION À VÉRIFIER:
{affirmation}

Réponds uniquement en format JSON :
{{"supporte": true/false, "raison": "Explication courte"}}
"""
    try:
        reponse = await llm.generate(prompt)
        # Nettoyage JSON basique
        texte = reponse.strip()
        if texte.startswith("```json"):
            texte = texte[7:]
        if texte.startswith("```"):
            texte = texte[3:]
        if texte.endswith("```"):
            texte = texte[:-3]
        
        data = json.loads(texte.strip())
        status = "✅ SUPPORTÉ" if data.get("supporte") else "❌ NON SUPPORTÉ (Hallucination)"
        return f"{status}\nRaison : {data.get('raison')}"
    except Exception as e:
        return f"Erreur lors de la vérification : {str(e)}\nRéponse brute: {reponse}"

if __name__ == "__main__":
    mcp.run()
