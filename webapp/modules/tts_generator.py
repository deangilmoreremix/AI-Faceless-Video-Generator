import pyttsx3
import os

def get_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    return [{'id': voice.id, 'name': voice.name} for voice in voices]

def text_to_speech(text, filename, voice_id=None):
    engine = pyttsx3.init()

    if voice_id:
        engine.setProperty('voice', voice_id)

    # The save_to_file method saves the speech to a file.
    # We'll save to a temporary mp3 and then convert to wav like before.
    temp_filename = "temp.mp3"
    engine.save_to_file(text, temp_filename)
    engine.runAndWait()

    os.system(f"ffmpeg -i {temp_filename} -ar 16000 -ac 1 {filename}")
    os.remove(temp_filename)
