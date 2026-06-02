"""
OpenTelemetry setup — Phase 7 observability.

Instruments the FastAPI app with distributed tracing.
Exports to Jaeger via OTLP when OTEL_EXPORTER_OTLP_ENDPOINT is set.
Falls back to no-op when not configured (no overhead in dev).
"""
import os

import structlog

log = structlog.get_logger()


def setup_telemetry(app) -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    service  = os.environ.get("OTEL_SERVICE_NAME", "companion-api")

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource(attributes={"service.name": service})
        provider = TracerProvider(resource=resource)

        if endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter  = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            log.info("otel_configured", endpoint=endpoint, service=service)
        else:
            log.info("otel_no_endpoint", note="tracing disabled — set OTEL_EXPORTER_OTLP_ENDPOINT")

        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

    except ImportError:
        log.warning("otel_not_installed", note="pip install opentelemetry-instrumentation-fastapi")
    except Exception as e:
        log.warning("otel_setup_failed", error=str(e))
