from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup OpenTelemetry Tracing
resource = Resource.create({
    "service.name": "midi_audio_processor",
    "service.instance.id": "instance-1",
})

# Set up the TracerProvider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

# OTLP Span Exporter for traces to localhost:4318
otlp_span_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")

# Add Span Processor to the tracer
span_processor = BatchSpanProcessor(otlp_span_exporter)
tracer_provider.add_span_processor(span_processor)

# Obtain tracer for use in the application
tracer = trace.get_tracer(__name__)

# Expose tracer for use in other modules
__all__ = ['tracer']
