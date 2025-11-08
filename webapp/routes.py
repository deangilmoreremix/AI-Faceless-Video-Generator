from flask import Blueprint, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, Video
from .tasks import create_video_task
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_login import LoginManager
import os
import uuid

bp = Blueprint('routes', __name__)

login_manager = LoginManager()
login_manager.login_view = 'routes.login'

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError('That username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@bp.route('/')
def index():
    return render_template('index.html', user=current_user)

@bp.route('/dashboard')
@login_required
def dashboard():
    videos = Video.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', videos=videos)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('routes.dashboard'))
    return render_template('login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('routes.login'))
    return render_template('register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.login'))

@bp.route('/generate-script', methods=['POST'])
@login_required
def generate_script():
    if 'topic' not in request.form:
        return jsonify({'error': 'Missing topic'}), 400

    topic = request.form['topic']
    from .modules.script_generator import get_script
    openai_api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
    script = get_script(topic, openai_api_key)
    return jsonify({'script': script})

@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    if 'script' not in request.form or 'avatar' not in request.files:
        return jsonify({'error': 'Missing script or avatar'}), 400

    script = request.form['script']
    avatar = request.files['avatar']

    # Save the avatar image
    avatar_filename = f"{uuid.uuid4()}_{avatar.filename}"
    image_path = os.path.join('uploads', avatar_filename)
    avatar.save(image_path)

    # Save the background music file if it exists
    music_path = None
    if 'background-music' in request.files and request.files['background-music'].filename != '':
        music = request.files['background-music']
        music_filename = f"{uuid.uuid4()}_{music.filename}"
        music_path = os.path.join('uploads', music_filename)
        music.save(music_path)

    voice_id = request.form.get('voice')
    aspect_ratio = request.form.get('aspect-ratio')
    resolution = request.form.get('resolution')

    # Start the video generation task
    task = create_video_task.delay(script, image_path, current_user.id, voice_id, music_path, aspect_ratio, resolution)

    return jsonify({'task_id': task.id})

@bp.route('/voices')
def voices():
    from .modules.tts_generator import get_voices
    return jsonify(get_voices())

@bp.route('/status/<task_id>')
def task_status(task_id):
    task = create_video_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'status': 'In progress...'}
    else:
        response = {'state': task.state, 'status': str(task.info)}
    return jsonify(response)

@bp.route('/results/<filename>')
@login_required
def uploaded_file(filename):
    video = Video.query.filter_by(video_path=os.path.join('results', filename)).first()
    if video and video.user_id == current_user.id:
        return send_from_directory('results', filename)
    else:
        return "Not authorized to view this video", 403
