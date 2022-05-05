from flask import Flask
from flask import render_template, redirect, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from data import db_session
from data.users import User
from data.news import News
from forms.user import RegisterForm, LoginForm, NewsForm
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
import PIL
from PIL import Image
import sqlite3
import os
import json


#connection = sqlite3.connect("db/blogs.db")
#cursor = connection.cursor()
#_emails = cursor.execute(f"SELECT email FROM users").fetchall()
#users = []
#f = open("static/members.json", mode='w')
#for i in _emails:
#    users.append({"email": i[0], "img": "static/galery/default.jpg"})
#f.write(json.dumps(users))
#f.close()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


@app.route("/")
def index():
    return render_template("home.html", news=news)

@app.route("/news")
def news():
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        news = db_sess.query(News).filter(
            (News.user == current_user) | (News.is_private != True))
    else:
        news = db_sess.query(News).filter(News.is_private != True)
    return render_template("index.html", news=news)

@app.route("/profile", methods=['POST', 'GET'])
def profile():
    if request.method == 'GET':
        db_sess = db_session.create_session()
        if current_user.is_authenticated:
            email = str(current_user).split()[-1]
            user = db_sess.query(User).filter(User.email == email).first()
            f = open("static/members.json")
            data = json.loads(f.read())
            for i in data:
                if i["email"] == email:
                    img = i["img"]
        else:
            news = db_sess.query(News).filter(News.is_private != True)
        return render_template("profile.html", user=user, img=img)
    elif request.method == 'POST':
        email = str(current_user).split()[-1]
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == email).first()
        file = request.files['file']
        if file:
            picture = Image.open(file)
            picture = picture.save(f"static/galery/{email}.jpg")
            file = open("static/members.json")
            data = json.loads(file.read())
            file.close()
            for i in data:
                if i["email"] == email:
                    i["img"] = f"static/galery/{email}.jpg"
                    img = i["img"]
            file = open("static/members.json", mode='w')
            file.write(json.dumps(data))
            file.close()
        return render_template("profile.html", user=user, img=img)

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id,
                                      News.user == current_user
                                      ).first()
    if news:
        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/add_news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('add_news.html',
                           title='Редактирование новости',
                           form=form
                           )


@app.route('/add_news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = News()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/')
    return render_template('add_news.html', title='Добавление новости',
                           form=form)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        f = open("static/members.json", mode="r")
        data = json.loads(f.read())
        f.close()
        data.append({"email": user.email, "img": "static/galery/default.jpg"})
        f = open("static/members.json", mode="w")
        f.write(json.dumps(data))
        f.close()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


if __name__ == '__main__':
    db_session.global_init("db/blogs.db")
    db_sess = db_session.create_session()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
