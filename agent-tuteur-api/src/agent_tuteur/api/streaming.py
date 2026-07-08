"""Formatage des événements Server-Sent Events (SSE)."""

from __future__ import annotations

import json
from typing import Any


def sse_event(payload: dict[str, Any]) -> str:
    """Sérialise un événement SSE ``data: <json>\\n\\n``."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
