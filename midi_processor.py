import time
from logging_setup import logger_area1
from tracing_setup import tracer
from helpers import velocity_to_dynamics, send_otlp_log
from opentelemetry.trace import StatusCode
from opentelemetry import trace
from opentelemetry.context import attach, detach

# Dictionary to track active notes
active_notes = {}

# Function to process MIDI input messages
def process_midi_message(msg, stream_id):
    global active_notes

    if msg.type == "note_on" and msg.velocity > 0:  # Note On
        if msg.note in active_notes:
            logger_area1.warning(f"Overlapping note_on for Note: {msg.note}. Ignoring.", extra={"stream_id": stream_id})
            return

        # Start a new trace (span)
        with tracer.start_as_current_span(f"note_{msg.note}") as span:
            span.set_attribute("stream_id", stream_id)
            span.set_attribute("note", msg.note)
            span.set_attribute("velocity_on", msg.velocity)
            span.set_attribute("dynamics", velocity_to_dynamics(msg.velocity))

            trace_id = format(span.get_span_context().trace_id, '032x')
            span_id = format(span.get_span_context().span_id, '016x')

            # Track the note's span and start time
            active_notes[msg.note] = {
                "span": span,
                "start_time": time.time()
            }

            # Attach span context to ensure logger has correct information
            token = attach(trace.set_span_in_context(span))

            try:
                # Log with the correct trace and span context
                logger_area1.info(
                    f"Note On - Note: {msg.note}, Velocity: {msg.velocity}, Dynamics: {velocity_to_dynamics(msg.velocity)}",
                    extra={"stream_id": stream_id}
                )

                # Send log
                send_otlp_log(
                    trace_id=trace_id,
                    span_id=span_id,
                    message=f"Note On received for Note: {msg.note}",
                    attributes=[
                        {"key": "note", "value": {"intValue": msg.note}},
                        {"key": "velocity", "value": {"intValue": msg.velocity}},
                    ],
                )
            finally:
                detach(token)

    elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):  # Note Off
        if msg.note not in active_notes:
            logger_area1.warning(f"Note Off received without a corresponding Note On for Note: {msg.note}", extra={"stream_id": stream_id})
            return

        # Retrieve the tracked note
        note_data = active_notes.pop(msg.note)
        span = note_data["span"]
        start_time = note_data["start_time"]
        elapsed_time = time.time() - start_time

        # Add attributes to the existing span and end it correctly
        with span:
            span.set_attribute("elapsed_time", elapsed_time)
            span.set_status(StatusCode.OK)

            # Attach span context to ensure logger has correct information
            token = attach(trace.set_span_in_context(span))

            try:
                # Emit log after span ends
                logger_area1.info(
                    f"Note Off - Note: {msg.note}, Elapsed: {elapsed_time:.3f} seconds",
                    extra={"stream_id": stream_id}
                )

                send_otlp_log(
                    trace_id=format(span.get_span_context().trace_id, '032x'),
                    span_id=format(span.get_span_context().span_id, '016x'),
                    message=f"Note Off processed for Note: {msg.note}",
                    attributes=[{"key": "elapsed_time", "value": {"doubleValue": elapsed_time}}],
                )
            finally:
                detach(token)
