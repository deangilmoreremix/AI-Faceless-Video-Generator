import speech_recognition as sr
import whisper
import os

def generate_srt(audio_path, srt_path):
    r = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = r.record(source)

    # Use Whisper to transcribe the audio with word-level timestamps
    result = r.recognize_whisper(audio, language="english", show_dict=True)

    srt_content = ""
    for i, segment in enumerate(result["segments"]):
        start_time = segment['start']
        end_time = segment['end']
        text = segment['text']

        # Format the timestamps into SRT format
        start_minutes, start_seconds = divmod(start_time, 60)
        start_hours, start_minutes = divmod(start_minutes, 60)
        start_milliseconds = int((start_time - int(start_time)) * 1000)
        start_srt_time = f"{int(start_hours):02}:{int(start_minutes):02}:{int(start_seconds):02},{start_milliseconds:03}"

        end_minutes, end_seconds = divmod(end_time, 60)
        end_hours, end_minutes = divmod(end_minutes, 60)
        end_milliseconds = int((end_time - int(end_time)) * 1000)
        end_srt_time = f"{int(end_hours):02}:{int(end_minutes):02}:{int(end_seconds):02},{end_milliseconds:03}"

        srt_content += f"{i + 1}\n{start_srt_time} --> {end_srt_time}\n{text.strip()}\n\n"

    with open(srt_path, 'w') as f:
        f.write(srt_content)
