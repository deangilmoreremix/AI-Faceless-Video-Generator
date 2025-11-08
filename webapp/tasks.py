from celery import Celery
import os
from . import create_app
from .models import db, Video
from .modules.script_generator import get_script
from .modules.tts_generator import text_to_speech
from .modules.video_generator import generate_video
from .modules.subtitle_generator import generate_srt

celery = Celery(__name__)

@celery.task
def create_video_task(script, image_path, user_id, voice_id=None, music_path=None, aspect_ratio="16:9", resolution="720p"):
    app = create_app()
    with app.app_context():
        # 1. Generate audio
        audio_filename = f"{uuid.uuid4()}.wav"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        text_to_speech(script, audio_path, voice_id)

        # 2. Mix audio if background music is provided
        final_audio_path = audio_path
        if music_path:
            mixed_audio_filename = f"{uuid.uuid4()}_mixed.wav"
            mixed_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], mixed_audio_filename)
            os.system(f"ffmpeg -i {audio_path} -i {music_path} -filter_complex \"[1:a]volume=0.3[a1];[0:a][a1]amix=inputs=2:duration=longest\" {mixed_audio_path}")
            final_audio_path = mixed_audio_path

        # 3. Generate subtitles
        srt_filename = f"{uuid.uuid4()}.srt"
        srt_path = os.path.join(app.config['UPLOAD_FOLDER'], srt_filename)
        generate_srt(final_audio_path, srt_path)

        # 4. Generate video with subtitles
        video_path = generate_video(image_path, final_audio_path, app.config['RESULT_FOLDER'])

        # Burn subtitles onto the video
        subtitled_video_filename = f"{uuid.uuid4()}_subtitled.mp4"
        subtitled_video_path = os.path.join(app.config['RESULT_FOLDER'], subtitled_video_filename)
        os.system(f"ffmpeg -i {video_path} -vf \"subtitles={srt_path}\" {subtitled_video_path}")

        # Format the video
        formatted_video_filename = f"{uuid.uuid4()}_formatted.mp4"
        formatted_video_path = os.path.join(app.config['RESULT_FOLDER'], formatted_video_filename)

        width, height = (1280, 720) if resolution == "720p" else (1920, 1080)
        if aspect_ratio == "9:16":
            width, height = height, width

        os.system(f"ffmpeg -i {subtitled_video_path} -vf \"scale={width}:{height},setsar=1\" {formatted_video_path}")

        # Save video to database
        new_video = Video(video_path=formatted_video_path, user_id=user_id)
        db.session.add(new_video)
        db.session.commit()

        return formatted_video_path
