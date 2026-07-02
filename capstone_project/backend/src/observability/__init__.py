"""
MVP observability: LangSmith (LLM tracing) + Prometheus/Grafana (metrics) +
a thin OpenTelemetry layer for function-level spans.

    from src.observability.telemetry import setup_observability
    from src.observability import metrics, tracing

    setup_observability()   # call once at startup in main.py
"""

from .telemetry import setup_observability

__all__ = ["setup_observability"]