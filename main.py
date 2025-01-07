import argparse
import mido
import keyboard
from threading import Thread, Event
from logging_setup import logger_area1 as logger
from audio import start_audio_recording, encode_audio_chunks
from midi_processor import process_midi_message
from helpers import stream_id
import time

# Define an Event to signal when to stop
stop_event = Event()

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="MIDI and Audio Processor")
    parser.add_argument("--mode", choices=["live", "file"], required=True,
                        help="Mode of operation: 'live' for live MIDI input, 'file' for input from a MIDI file")
    parser.add_argument("--output-file", type=str, required=True,
                        help="File name for saving recorded audio")
    parser.add_argument("--input-file", type=str,
                        help="Input MIDI file to be processed (required if mode is 'file')")

    args = parser.parse_args()

    # Handle mode: live or file
    if args.mode == "live":
        logger.info("Running in live MIDI input mode.")

        # Print available MIDI input ports
        logger.info("Available MIDI input ports:")
        for i, port in enumerate(mido.get_input_names()):
            logger.info(f"{i}: {port}")

        # Select the first MIDI input port as default
        midi_input_ports = mido.get_input_names()
        if len(midi_input_ports) == 0:
            logger.error("No MIDI input ports available. Please connect a MIDI device.")
            return

        midi_input_port = midi_input_ports[0]
        logger.info(f"Using MIDI input port: {midi_input_port}")

        # Start audio recording in a separate thread
        audio_thread = Thread(target=start_audio_recording, args=(44100, 1, stop_event))
        encode_thread = Thread(target=encode_audio_chunks, args=(args.output_file, stream_id))

        audio_thread.start()
        encode_thread.start()

        logger.info("Listening for MIDI input (Press Page Down to stop)...")
        try:
            with mido.open_input(midi_input_port) as port:
                while not stop_event.is_set():
                    if keyboard.is_pressed("page down"):
                        logger.info("Page Down pressed, stopping...")
                        stop_event.set()  # Signal all threads to stop

                    for msg in port.iter_pending():
                        logger.debug(f"Received MIDI message: {msg}")
                        process_midi_message(msg, stream_id)

        except Exception as e:
            logger.error(f"Error processing MIDI input: {e}")

        audio_thread.join()
        encode_thread.join()

    elif args.mode == "file":
        if not args.input_file:
            logger.error("Input file must be provided in 'file' mode. Use --input-file to specify the MIDI file.")
            return

        logger.info(f"Running in MIDI file input mode. Processing file: {args.input_file}")

        # Start audio recording in a separate thread
        audio_thread = Thread(target=start_audio_recording, args=(44100, 1, stop_event))
        encode_thread = Thread(target=encode_audio_chunks, args=(args.output_file, stream_id))

        audio_thread.start()
        encode_thread.start()

        logger.info(f"Processing MIDI file: {args.input_file}")
        try:
            midi_file = mido.MidiFile(args.input_file)
            for msg in midi_file.play():
                if stop_event.is_set():
                    break
                logger.debug(f"Processing MIDI file message: {msg}")
                process_midi_message(msg, stream_id)
        except Exception as e:
            logger.error(f"Error processing MIDI file: {e}")

        audio_thread.join()
        encode_thread.join()

if __name__ == "__main__":
    main()
