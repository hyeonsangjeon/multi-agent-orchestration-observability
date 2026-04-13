"""OpenTelemetry + Azure Application Insights setup for routing observability."""

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def setup_telemetry() -> trace.Tracer:
    """Configure OpenTelemetry tracing.

    If APPLICATIONINSIGHTS_CONNECTION_STRING is set, traces go to App Insights.
    Otherwise a console exporter is used as fallback.
    """
    resource = Resource.create({"service.name": "routing-observability-demo"})
    provider = TracerProvider(resource=resource)

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            exporter = AzureMonitorTraceExporter(connection_string=connection_string)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            print("[Telemetry] ✅ Azure Monitor exporter configured.")
        except ImportError:
            print("[Telemetry] ⚠️ azure-monitor-opentelemetry-exporter not installed. Using console exporter.")
            _add_console_exporter(provider)
        except Exception as e:
            print(f"[Telemetry] ⚠️ Azure Monitor exporter failed ({type(e).__name__}: {e}). Using console exporter.")
            _add_console_exporter(provider)
    else:
        print("[Telemetry] ℹ️ No APPLICATIONINSIGHTS_CONNECTION_STRING. Using console exporter.")
        _add_console_exporter(provider)

    trace.set_tracer_provider(provider)
    return trace.get_tracer("routing-observability")


def _add_console_exporter(provider: TracerProvider) -> None:
    """Add a console span exporter for local development."""
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
