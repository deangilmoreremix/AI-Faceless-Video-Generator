from flask import Flask
from .models import db
from .tasks import celery

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'thisisadefaultsecretkey')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['RESULT_FOLDER'] = 'results'
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

    db.init_app(app)
    celery.conf.update(app.config)

    from .routes import login_manager
    login_manager.init_app(app)

    from . import routes
    app.register_blueprint(routes.bp)

    return app
