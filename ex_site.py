import sqlite3
import os
from flask import Flask, render_template, request, g, flash, abort, \
    redirect, url_for, make_response
from FDataBase import FDataBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, \
    current_user, logout_user
from UserLogin import UserLogin
from forms import LoginForm, RegisterForm
from admin.admin import admin

DATABASE = '/tmp/ex_site.db'
DEBUG = True
SECRET_KEY = '0n2vvy7t5yv2745yvb2745n27v507yv02057yv247n79vyt2975tyn25y'
MAX_CONTENT_LENGTH = 1024 * 1024

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(DATABASE=os.path.join(app.root_path, 'ex_site.db')))

app.register_blueprint(admin, url_prefix='/admin')

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Авторизуйтесь, чтобы просматривать новости"
login_manager.login_message_category = "success"


@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id, dbase)


def connect_db():
    """Связь с таблицей."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    """Создание таблицы."""
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


def get_db():
    """Соединение с БД, если оно не установлено."""
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


dbase = None
@app.before_request
def before_request():
    """Установление связи с БД перед выполнением запроса."""
    global dbase
    db = get_db()
    dbase = FDataBase(db)


@app.route("/")
def index():
    return render_template('index.html', posts=dbase.getPostsAnonce(),
                           title='Главная')


@app.route("/about")
def about():
    return render_template('about.html', title='О сайте')


@app.route("/add_post", methods=['POST', 'GET'])
def add_post():
    title = "Добавить статью"
    if request.method == 'POST':
        if len(request.form['name']) > 4 and len(request.form['post']) > 10:
            res = dbase.addPost(request.form['name'], request.form['post'],
                                request.form['url'])
            if not res:
                flash('Ошибка добавления статьи', category='error')
            else:
                flash('Статья успешно добавлена', category='success')
        else:
            flash('Ошибка добавления статьи', category='error')
    return render_template('add_post.html', title=title)


@app.route("/post/<alias>")
@login_required
def showPost(alias):
    title, post = dbase.getPost(alias)
    if not title:
        abort(404)
    return render_template('post.html', title=title, post=post)


@app.teardown_appcontext
def close_db(error):
    """Прерываем связь с БД, если оно установлено."""
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = LoginForm()
    if form.validate_on_submit():
        user = dbase.getUserByEmail(form.email.data)
        if user and check_password_hash(user['psw'], form.psw.data):
            userlogin = UserLogin().create(user)
            rm = form.remember.data
            login_user(userlogin, remember=rm)
            return redirect(request.args.get("next") or url_for('profile'))
        flash("Неверная пара логин/пароль", "error")
    return render_template("login.html", title="Авторизация", form=form)


@app.route("/register", methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
            hash = generate_password_hash(form.psw.data)
            res = dbase.addUser(form.name.data, form.email.data, hash)
            if res:
                flash('Вы успешно зарегистрировались', category='success')
                return redirect(url_for('login'))
            else:
                flash('Ошибка при добавлении в БД', category='error')
    return render_template('register.html', title='Регистрация', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "success")
    return redirect(url_for('login'))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", title="Профиль")


@app.route("/userava")
@login_required
def userava():
    img = current_user.getAvatar(app)
    if not img:
        return ""
    h = make_response(img)
    h.headers['Content-Type'] = 'image/png'
    return h


@app.route("/upload", methods=["POST", "GET"])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and current_user.verifyExt(file.filename):
            try:
                img = file.read()
                res = dbase.updateUserAvatar(img, current_user.get_id())
                if not res:
                    flash("Ошибка обновления аватара", "error")
                flash("Аватар обновлён", "success")
            except FileNotFoundError as e:
                flash("Ошибка обновления аватара", "error")
    return redirect(url_for('profile'))


if __name__ == "__main__":
    app.run(debug=True)

# create_db()
