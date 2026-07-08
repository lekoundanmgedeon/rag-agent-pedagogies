"""Agent Tuteur Sénégal — cœur métier (RAG + agent pédagogique).

Le paquet est organisé en couches strictement découplées d'un framework web :
``config`` (réglages+taxonomie), ``domain`` (modèles), ``ingestion``,
``vectorstore``, ``tools``, ``agent``. Les couches API/persistance (étapes 4+)
consomment ce cœur sans que le cœur ne les connaisse.
"""

__version__ = "0.1.0"
