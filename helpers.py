import time
import requests
import json
from logging_setup import logger_area1 as logger  # Use logger_area1 and alias it as logger

# Generate unique identifier for this stream
from datetime import datetime
stream_id = f"capture-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def velocity_to_dynamics(velocity):
    if velocity < 40:
        return "pp"
    elif velocity < 70:
        return "mf"
    elif velocity < 100:
        return "f"
    else:
        return "ff"

# OTLP Log Sender
def send_otlp_log(trace_id, span_id, message, level="INFO", attributes=None):
    """
    Send an OTLP log record to the OpenTelemetry Collector.
    """
    url = "http://localhost:4318/v1/logs"
    log_record = {
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "midi_processor"}}
            ]
        },
        "scopeLogs": [
            {
                "scope": {"name": "midi_audio_logs"},
                "logRecords": [
                    {
                        "timeUnixNano": int(time.time() * 1e9),
                        "severityText": level,
                        "body": {"stringValue": message},
                        "traceId": trace_id,
                        "spanId": span_id,
                        "attributes": attributes or [],
                    }
                ],
            }
        ],
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(log_record), headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to send log: {response.text}")
    logger.info(f"Log sent: {message}")
