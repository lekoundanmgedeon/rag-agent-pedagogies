"""Attentes par cas QA — l'assertion associée à un ``id`` du backlog.

Le JSON fournit le *prompt* (la fixture), ce module fournit le *verdict*. Un cas
présent dans le backlog mais absent d'ici est signalé ``xfail`` par le rejeu
générique : il reste visible dans le rapport pytest au lieu de disparaître
silencieusement. C'est ce qui garantit qu'un cas ne peut pas être « oublié ».

Au fil des sprints, une entrée est ajoutée ici en même temps que le correctif.
"""

from __future__ import annotations

from collections.abc import Callable

#: Signature d'une attente : reçoit l'``AgentResult`` du rejeu et le cas.
Attente = Callable[[object, object], None]

ATTENTES: dict[int, Attente] = {}
