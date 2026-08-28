from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config.otel import OtelSettings

_configured = False


def setup_otel(settings: OtelSettings) -> None:
    """Inisialisasi OpenTelemetry sekali per proses.

    - `OTEL_ENABLED=true` → ekspor span via OTLP HTTP ke collector
      (`OTEL_EXPORTER_OTLP_ENDPOINT`).
    - selain itu → span ditulis ke console (dev fallback), supaya tracing tetap
      terlihat tanpa collector.
    """
    global _configured

    if _configured:
        return

    resource = Resource.create(
        {"service.name": settings.service_name}
    )

    provider = TracerProvider(resource=resource)

    if settings.enabled:
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{settings.exporter_otlp_endpoint}/v1/traces"
                )
            )
        )
    else:
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(provider)

    _configured = True


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
