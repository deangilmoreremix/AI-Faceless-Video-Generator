from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import uuid
from celery import Celery

# App configuration
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# Celery initialization
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Import modules
from modules.script_generator import get_script
from modules.tts_generator import text_to_speech
from modules.video_generator import generate_video

# Define Celery task
@celery.task
def create_video_task(script, image_path, voice_id=None, music_path=None):
    # 1. Generate audio
    audio_filename = f"{uuid.uuid4()}.wav"
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
    text_to_speech(script, audio_path, voice_id)

    # 2. Mix audio if background music is provided
    final_audio_path = audio_path
    if music_path:
        mixed_audio_filename = f"{uuid.uuid4()}_mixed.wav"
        mixed_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], mixed_audio_filename)
        # Mix the two audio files, reducing the background music volume
        os.system(f"ffmpeg -i {audio_path} -i {music_path} -filter_complex \"[1:a]volume=0.3[a1];[0:a][a1]amix=inputs=2:duration=longest\" {mixed_audio_path}")
        final_audio_path = mixed_audio_path

    # 3. Generate video
    # This assumes SadTalker is in the parent directory. This will need to be configured.
    # We also need to handle the SadTalker model downloads.
    video_path = generate_video(image_path, final_audio_path, app.config['RESULT_FOLDER'])

    return video_path

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-script', methods=['POST'])
def generate_script():
    if 'topic' not in request.form:
        return jsonify({'error': 'Missing topic'}), 400

    topic = request.form['topic']
    openai_api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
    script = get_script(topic, openai_api_key)
    return jsonify({'script': script})

@app.route('/generate', methods=['POST'])
def generate():
    if 'script' not in request.form or 'avatar' not in request.files:
        return jsonify({'error': 'Missing script or avatar'}), 400

    script = request.form['script']
    avatar = request.files['avatar']

    # Save the avatar image
    avatar_filename = f"{uuid.uuid4()}_{avatar.filename}"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
    avatar.save(image_path)

    # Save the background music file if it exists
    music_path = None
    if 'background-music' in request.files and request.files['background-music'].filename != '':
        music = request.files['background-music']
        music_filename = f"{uuid.uuid4()}_{music.filename}"
        music_path = os.path.join(app.config['UPLOAD_FOLDER'], music_filename)
        music.save(music_path)

    voice_id = request.form.get('voice')

    # Start the video generation task
    task = create_video_task.delay(script, image_path, voice_id, music_path)

    return jsonify({'task_id': task.id})

@app.route('/voices')
def voices():
    from modules.tts_generator import get_voices
    return jsonify(get_voices())

@app.route('/status/<task_id>')
def task_status(task_id):
    task = create_video_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'status': task.info.get('status', '')}
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        response = {'state': task.state, 'status': str(task.info)}
    return jsonify(response)

@app.route('/results/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
