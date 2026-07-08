"""Logging structuré (JSON) partagé par l'API et le worker.

Chaque événement métier (nœud d'agent, étape d'ingestion) est loggé en JSON
sur stdout (consultable via ``docker compose logs -f api worker``) **et** dans
un fichier rotatif dédié au service (``logs/<service>.log``), avec un
identifiant de corrélation (``trace_id`` pour un tour de chat, ``document_id``
pour une ingestion) qui permet de reconstituer le fil complet d'une requête
sans avoir à grep plusieurs flux.

Ce module ne fait que du logging : il n'est pas la source de vérité de l'état
(qui reste en base — ``messages.trace``, ``documents.log``). Les logs servent
au diagnostic technique en temps réel ; l'état persisté sert à l'affichage
Streamlit après coup.

**Isolation du contexte métier.** ``log_event`` place tout le contexte sous
une unique clé (``record.ctx``) plutôt que d'utiliser ``extra=`` à plat : le
module ``logging`` de la stdlib réserve des noms d'attribut sur ``LogRecord``
(``filename``, ``module``, ``name``, ``process``, ``args``…) et lève
``KeyError`` — ou pire, écrase silencieusement un champ standard — si un champ
métier porte le même nom (ex. un document dont on veut logger ``filename``, ou
un niveau d'indice pédagogique nommé ``level``). Nommer tout sous ``ctx``
élimine cette classe de bug plutôt que d'obliger à mémoriser une liste de noms
interdits.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    """Sérialise chaque enregistrement de log en une ligne JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "log_level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        ctx = getattr(record, "ctx", None)
        if ctx:
            payload.update(ctx)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(service: str, level: int = logging.INFO) -> None:
    """Configure le logging JSON (stdout + fichier) pour ce processus.

    Idempotent : un second appel (ex. rechargement `uvicorn --reload`) ne
    duplique pas les handlers.
    """
    root = logging.getLogger()
    if getattr(root, "_agent_tuteur_configured", False):
        return
    root.setLevel(level)

    formatter = JsonFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    try:
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{service}.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Système de fichiers en lecture seule ou répertoire non créable :
        # le logging stdout suffit (ex. certains environnements conteneurisés
        # restreints). Ne jamais faire planter l'application pour un log.
        pass

    root._agent_tuteur_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, message: str, *, log_level: int = logging.INFO, **context: Any) -> None:
    """Log un événement structuré : ``message`` + champs de contexte nommés.

    ``log_level`` (et non ``level``) pour ne jamais entrer en collision avec un
    champ métier nommé ``level`` (ex. le niveau d'indice pédagogique 0-4).
    Tout ``context`` voyage sous une seule clé ``ctx`` (cf. docstring du
    module) : aucun nom de champ métier n'est interdit.
    """
    logger.log(log_level, message, extra={"ctx": context})
