import wave
import base64
import time
import requests
import moviepy.editor as mp
from queue import Queue
import sounddevice as sd
from threading import Event
from logging_setup import logger_area1
from helpers import send_otlp_log

# Imgur Client ID (replace with your own)
IMGUR_CLIENT_ID = "49ce43a981d2b15"

# Audio queue to manage audio data between threads
audio_queue = Queue()

# Function to start audio recording
def start_audio_recording(samplerate, channels, stop_event):
    """
    Start recording audio from the input device and push chunks into a queue.
    Recording stops when the `stop_event` is set.
    """
    with sd.InputStream(callback=audio_callback, samplerate=samplerate, channels=channels, dtype="int16"):
        logger_area1.info("Recording audio... Press Page Down to stop.")
        while not stop_event.is_set():
            time.sleep(0.1)
    audio_queue.put(None)  # Signal the end of audio capture

# Audio callback function to handle incoming audio data
def audio_callback(indata, frames, time, status):
    if status:
        logger_area1.warning(f"Audio status: {status}")
    audio_queue.put(indata.copy())

# Function to base64 encode audio chunks and log them
def encode_audio_chunks(output_file, stream_id):
    """
    Encode audio chunks and write to a wave file, while sending logs to OTLP.
    """
    output_file = f"{output_file}{stream_id}.wav"
    with wave.open(output_file, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(44100)
        
        chunk_counter = 0
        base64_data_accumulator = []

        while True:
            data = audio_queue.get()
            if data is None:
                break

            # Write raw audio data to the file
            wf.writeframes(data)

            # Accumulate data to batch logs
            base64_chunk = base64.b64encode(data).decode("utf-8")
            base64_data_accumulator.append(base64_chunk)

            chunk_counter += 1

            # Send log after accumulating 10 chunks
            if chunk_counter >= 10:
                combined_data = "".join(base64_data_accumulator[:10])  # Take only the first 10 accumulated chunks
                send_otlp_log(
                    trace_id="",
                    span_id="",
                    message=f"Audio chunk batch for stream {stream_id}",
                    attributes=[{"key": "encoded_audio_batch", "value": {"stringValue": combined_data[:50]}}],  # Limit the size of data sent
                )
                logger_area1.info(f"Batch Log sent: {chunk_counter} chunks for stream {stream_id}")

                # Reset counter and accumulator
                chunk_counter = 0
                base64_data_accumulator = []

        # Flush remaining chunks
        if base64_data_accumulator:
            combined_data = "".join(base64_data_accumulator)
            send_otlp_log(
                trace_id="",
                span_id="",
                message=f"Final audio chunk batch for stream {stream_id}",
                attributes=[{"key": "encoded_audio_batch", "value": {"stringValue": combined_data[:50]}}],  # Limit the size of data sent
            )
            logger_area1.info(f"Final Batch Log sent: {len(base64_data_accumulator)} chunks for stream {stream_id}")

        logger_area1.info(f"Audio saved to {output_file}")

    # Convert the .wav file to an .mp4 video
    mp4_output = output_file.replace(".wav", ".mp4")
    convert_wav_to_mp4(output_file, mp4_output)

    # Upload the mp4 file to Imgur and generate a link
    imgur_link = upload_to_imgur(mp4_output)
    if imgur_link:
        logger_area1.info(f"Imgur link for the audio visualization: {imgur_link}")

# Function to convert .wav to .mp4
def convert_wav_to_mp4(wav_file, mp4_output):
    """
    Convert a WAV file to an MP4 video file.
    """
    try:
        # Create a moviepy AudioFileClip object
        audio_clip = mp.AudioFileClip(wav_file)
        
        # Set the duration and create a simple visual (black screen for now)
        duration = audio_clip.duration
        video_clip = mp.ColorClip(size=(640, 480), color=(0, 0, 0), duration=duration)
        
        # Set the audio to the video
        video_clip = video_clip.set_audio(audio_clip)
        
        # Write the result to an MP4 file
        video_clip.write_videofile(mp4_output, fps=24)
        
        logger_area1.info(f"MP4 video saved to {mp4_output}")
    except Exception as e:
        logger_area1.error(f"Failed to convert WAV to MP4: {e}")

# Function to upload a file to Imgur using an HTTP POST request
def upload_to_imgur(file_path):
    """
    Upload the specified file to Imgur and return a shareable link.
    """
    headers = {
        "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
    }
    try:
        with open(file_path, "rb") as file:
            response = requests.post(
                "https://api.imgur.com/3/upload",
                headers=headers,
                files={"video": file},
            )

        response_data = response.json()

        if response.status_code == 200 and response_data.get("success"):
            imgur_link = response_data["data"]["link"]
            logger_area1.info(f"File uploaded to Imgur successfully: {imgur_link}")
            return imgur_link
        else:
            logger_area1.error(f"Failed to upload to Imgur: {response_data}")
            return None
    except Exception as e:
        logger_area1.error(f"Exception occurred during upload to Imgur: {e}")
        return None
