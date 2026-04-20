"""OpenTelemetry + Azure Application Insights setup for routing observability."""

import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

_TELEMETRY_LOGGER = logging.getLogger("routing_observability.telemetry")
_PROVIDER_INITIALIZED = False


def setup_telemetry() -> trace.Tracer:
    """Configure OpenTelemetry tracing (idempotent).

    If APPLICATIONINSIGHTS_CONNECTION_STRING is set, traces go to App Insights
    via a BatchSpanProcessor. Otherwise a console exporter is used as fallback.
    Re-invocation reuses the existing global TracerProvider rather than trying
    to override it (which OTel forbids and silently ignores).
    """
    global _PROVIDER_INITIALIZED
    if _PROVIDER_INITIALIZED:
        return trace.get_tracer("routing-observability")

    resource = Resource.create({"service.name": "routing-observability-demo"})
    provider = TracerProvider(resource=resource)

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            exporter = AzureMonitorTraceExporter(connection_string=connection_string)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            _TELEMETRY_LOGGER.info("Azure Monitor exporter configured.")
        except ImportError:
            _TELEMETRY_LOGGER.warning(
                "azure-monitor-opentelemetry-exporter not installed. Using console exporter."
            )
            _add_console_exporter(provider)
        except Exception as e:
            _TELEMETRY_LOGGER.warning(
                "Azure Monitor exporter failed (%s: %s). Using console exporter.",
                type(e).__name__, e,
            )
            _add_console_exporter(provider)
    else:
        _TELEMETRY_LOGGER.info(
            "No APPLICATIONINSIGHTS_CONNECTION_STRING. Using console exporter."
        )
        _add_console_exporter(provider)

    trace.set_tracer_provider(provider)
    _PROVIDER_INITIALIZED = True
    return trace.get_tracer("routing-observability")


def _add_console_exporter(provider: TracerProvider) -> None:
    """Add a console span exporter for local development."""
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    # SimpleSpanProcessor is fine for the local console — it keeps cell output
    # in execution order.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
