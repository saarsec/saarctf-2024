import os
import secrets
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

from db.models import User
from db.repository import DbRepository
from views.auth import AuthView
from views.ipp_server import IppView
from views.web import WebsiteView


def get_secret_key(data_dir: Path) -> str:
    fname = data_dir / 'secret.txt'
    try:
        return fname.read_text().strip()
    except FileNotFoundError:
        key = secrets.token_hex(16)
        fname.write_text(key)
        fname.chmod(0o600)
        return key


def create_app(data_dir: Path, repo: DbRepository) -> Flask:
    app = Flask('rent-a-printer')
    app.config['SECRET_KEY'] = get_secret_key(data_dir)
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: int) -> User | None:
        return repo.users.by_id(user_id)

    app.register_blueprint(AuthView(data_dir, repo).blueprint())
    app.register_blueprint(WebsiteView(data_dir, repo).blueprint())
    app.register_blueprint(IppView(data_dir, repo).blueprint())
    return app


def default_app() -> Flask:
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(mode=0o750, exist_ok=True)

    repo = DbRepository(data_dir / 'db.sqlite3')
    return create_app(data_dir, repo)


if __name__ == '__main__':
    default_app().run(host='0.0.0.0', port=6310, debug=False)
