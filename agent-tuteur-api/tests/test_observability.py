import json
import logging

from agent_tuteur.observability import JsonFormatter, log_event


def _make_record_output(**context) -> dict:
    logger = logging.getLogger("test_observability")
    logger.setLevel(logging.DEBUG)
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture()
    logger.addHandler(handler)
    try:
        log_event(logger, "some:event", **context)
    finally:
        logger.removeHandler(handler)

    formatter = JsonFormatter()
    return json.loads(formatter.format(records[0]))


def test_context_fields_appear_in_json_output():
    payload = _make_record_output(trace_id="abc", node="retrieve_context", duration_ms=1.5, n_sources=3)
    assert payload["message"] == "some:event"
    assert payload["trace_id"] == "abc"
    assert payload["node"] == "retrieve_context"
    assert payload["duration_ms"] == 1.5
    assert payload["n_sources"] == 3


def test_business_field_named_level_does_not_collide_with_log_level():
    """Régression : un champ métier `level` (ex. niveau d'indice pédagogique)
    ne doit jamais être interprété comme le niveau de log Python — sinon
    l'événement est silencieusement filtré (cf. bug du nœud diagnose_hint_level)."""
    logger = logging.getLogger("test_observability_level")
    logger.setLevel(logging.INFO)
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture()
    logger.addHandler(handler)
    try:
        # `level=1` est une valeur métier ; si mal nommé, cela serait interprété
        # comme logging.Handler level=1 (< INFO) et le record serait filtré.
        log_event(logger, "node:diagnose_hint_level", trace_id="abc", node="diagnose_hint_level", level=1)
    finally:
        logger.removeHandler(handler)

    assert len(records) == 1
    formatter = JsonFormatter()
    payload = json.loads(formatter.format(records[0]))
    # Le champ métier `level` (niveau d'indice) reste distinct de `log_level`
    # (sévérité du log) : aucune collision, aucune perte d'information.
    assert payload["level"] == 1
    assert payload["log_level"] == "INFO"
    assert payload["message"] == "node:diagnose_hint_level"


def test_business_fields_reserved_by_logrecord_do_not_raise():
    """Régression : des champs métier aussi anodins que `filename` ou `module`
    sont des attributs RÉSERVÉS de logging.LogRecord — les passer via `extra=`
    à plat lève KeyError. log_event doit les isoler sans jamais planter."""
    payload = _make_record_output(
        filename="cours.md", module="mathematiques", name="ignored", process="ingestion"
    )
    assert payload["filename"] == "cours.md"
    assert payload["module"] == "mathematiques"
