import re

from flask import request, flash, redirect, url_for, Blueprint, Response, render_template
from flask_login import login_user, current_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from db.models import User
from views.web import View


class AuthView(View):
    def login(self) -> str:
        if current_user.is_authenticated:
            return redirect(url_for('web.user_view'))
        return render_template("login.html", user=current_user)

    def login_post(self) -> Response:
        name = request.form.get('name')
        password = request.form.get('password')

        user = self.repo.users.by_name(name)
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid user/password')
            return redirect(url_for('auth.login'))

        login_user(user, remember=False)
        return redirect(url_for('web.user_view'))

    def signup(self) -> str:
        if current_user.is_authenticated:
            return redirect(url_for('web.user_view'))
        return render_template("signup.html", user=current_user)

    def signup_post(self) -> Response:
        name = request.form.get('name')
        password = request.form.get('password')
        if not name or not re.match(r'^[a-zA-Z0-9]{3,48}$', name):
            flash('Invalid username')
            return redirect(url_for('auth.signup'))
        if not password or len(password) < 8:
            flash('Password too short')
            return redirect(url_for('auth.signup'))
        if self.repo.users.by_name(name) is not None:
            flash('Username already taken')
            return redirect(url_for('auth.signup'))

        new_user = User(0, name=name, password_hash=generate_password_hash(password))
        self.repo.users.store(new_user)
        (self.data_dir / new_user.name).mkdir(mode=0o750, exist_ok=True)

        login_user(new_user, remember=False)
        return redirect(url_for('web.user_view'))

    @login_required
    def signout(self) -> Response:
        logout_user()
        return redirect(url_for('web.index'))

    def blueprint(self) -> Blueprint:
        bp = Blueprint('auth', __name__)
        bp.add_url_rule('/login', None, self.login, methods=['GET'])
        bp.add_url_rule('/login', None, self.login_post, methods=['POST'])
        bp.add_url_rule('/signup', None, self.signup, methods=['GET'])
        bp.add_url_rule('/signup', None, self.signup_post, methods=['POST'])
        bp.add_url_rule('/signout', None, self.signout, methods=['POST'])
        return bp
