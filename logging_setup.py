import logging
import json
from datetime import datetime
from opentelemetry import trace

class JSONFileHandler(logging.FileHandler):
    def emit(self, record):
        try:
            # Manually format the log record time
            log_time = datetime.fromtimestamp(record.created).isoformat()

            # Format the log record as a JSON object
            log_entry = {
                "time": log_time,
                "level": record.levelname,
                "message": record.getMessage(),
                "name": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "service_name": "midi_audio_processor",
                "trace_id": getattr(record, "trace_id", "0000000000000000"),
                "span_id": getattr(record, "span_id", "0000000000000000"),
                "stream_id": getattr(record, "stream_id", "unknown_stream_id"),  # Update to correctly include stream_id
            }

            # Write the JSON entry to the file
            with open(self.baseFilename, 'a') as file:
                file.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error while writing log to JSON file: {e}")

class OpenTelemetryLoggingFilter(logging.Filter):
    def filter(self, record):
        # Get the current span
        current_span = trace.get_current_span()

        if current_span is not None and current_span.get_span_context().is_valid:
            span_context = current_span.get_span_context()
            record.trace_id = format(span_context.trace_id, '032x')
            record.span_id = format(span_context.span_id, '016x')
        else:
            record.trace_id = "0000000000000000"
            record.span_id = "0000000000000000"

        return True

# Configure logger to write JSON logs to a file
json_log_handler = JSONFileHandler('application_logs.json')
json_log_handler.setLevel(logging.INFO)

# Set up formatting - you can use a simple formatter since we use a custom format in JSON
formatter = logging.Formatter('%(message)s')
json_log_handler.setFormatter(formatter)

# Set up root logger
logger_area1 = logging.getLogger('midi_audio_processor.area1')
logger_area1.setLevel(logging.INFO)
logger_area1.addHandler(json_log_handler)

# Attach a stream handler to also log to the console for debugging purposes
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger_area1.addHandler(console_handler)

# Add the custom filter to logger_area1
otel_filter = OpenTelemetryLoggingFilter()
logger_area1.addFilter(otel_filter)

# Expose the logger for other modules
__all__ = ['logger_area1']
