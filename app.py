from flask import Flask, render_template, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField, EmailField
from wtforms.validators import InputRequired, Length, Email
from flask_login import LoginManager, login_required, current_user, login_user, logout_user, UserMixin
import json
import time
from datetime import timedelta, datetime
import math

with open('config.json', 'r') as f:
    data = json.load(f)

app = Flask(__name__)
if data["config"]["local_server"]:
    app.config["SQLALCHEMY_DATABASE_URI"] = data["config"]["local_db"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = data["config"]["production_db"]
app.config["SQLACHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = data["config"]["secret_key"]
db = SQLAlchemy(app)
login_manager=LoginManager(app)
login_manager.login_view='dashboard'

@login_manager.user_loader
def load_user(id):
    return Admin.query.get(int(id))

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    pw = db.Column(db.String(50), nullable=False)

class Articles(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    slug = db.Column(db.String(200), unique=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(200), nullable=False, default=None)
    article = db.Column(db.String(20000), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    link= db.Column(db.String(200), nullable=False, default=None)
    date = db.Column(db.Integer(), nullable=False)

class AdminForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    pw = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

class ArticleForm(FlaskForm):
    slug = StringField('Slug', validators=[InputRequired(), Length(min=10, max=50)])
    title = StringField('Title', validators=[InputRequired(), Length(min=10, max=200)])
    subtitle = StringField('Sub-Title', validators=[InputRequired(), Length(min=10, max=200)])
    article = StringField('Article', validators=[InputRequired(), Length(min=10, max=20000)])
    submit = SubmitField('Post')

class EventForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(min=10, max=200)])
    link = StringField('Link', validators=[InputRequired(), Length(min=10, max=200)])
    date = StringField('Article', validators=[InputRequired()])
    submit = SubmitField('Post')

class ContactForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    subject = StringField('Subject', validators=[InputRequired(), Length(min=10, max=200)])
    message = TextAreaField('Message', validators=[InputRequired()])
    submit = SubmitField('Contact')

class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(2000), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/', methods=["GET","POST"])
def home():
    return render_template("home.html")

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    form = AdminForm()
    form1 = EventForm()
    articles = Articles.query.all()
    event = Event.query.all()
    if current_user.is_authenticated:
        return render_template("dashboard.html", articles=articles, event=event)
    if form.validate_on_submit():
        user = Admin.query.filter_by(username=form.username.data).first()
        if user:
            if form.pw.data==user.pw:
                login_user(user)
                return render_template("dashboard.html", articles=articles, event=event)
            else:
                flash("Invalid Password")
        else:
            flash(f"{form.username.data} is not an admin", 'danger')
    return render_template('dash_login.html', form=form, articles=articles, form1=form1, event=event)

@app.route('/dashboard/manage-articles/<int:id>', methods=['GET','POST'])
@login_required
def manage_articles(id):
    form = ArticleForm()
    if request.method=='POST':
        if id==0:
            db.session.add(Articles(slug=form.slug.data, title=form.title.data, subtitle=form.subtitle.data, article=form.article.data))
            db.session.commit()
            nextSlug = data['posts']['slug'].split('-')
            nextSlug[1] = f"{data['posts']['id']+1}"
            nextID=data['posts']['id']+1
            total_posts = data['posts']['total_posts']+1
            data['posts']={}
            data['posts']['id'] = nextID
            data['posts']['slug'] = '-'.join(nextSlug)
            data['posts']['total_posts'] = total_posts
            with open('config.json', 'w') as f:
                json.dump(data, f, indent=4)
        else:
            article = Articles.query.filter_by(id=id).first()
            article.title=form.title.data
            article.subtitle=form.subtitle.data
            article.article = form.article.data
            db.session.add(article)
            db.session.commit()   
    article1=Articles.query.filter_by(id=id).first()
    return render_template('articleform.html', id=id, form=form, article1=article1, data=data)

@app.route('/dashboard/delete-article/<int:id>', methods=['GET','POST'])
@login_required
def delete_article(id):
    article = Articles.query.filter_by(id=id).first()
    db.session.delete(article)
    db.session.commit()
    total_posts = data["posts"]["total_posts"]-1
    data["posts"]["total_posts"] = total_posts
    with open('config.json', 'w') as f:
        json.dump(data, f, indent=4)
    return redirect('/dashboard')

@app.route('/dashboard/manage-event/<int:id>', methods=['GET','POST'])
@login_required
def manage_event(id):
    form = EventForm()
    if request.method=='POST':
        if id==0:
            date = datetime.utcnow()+timedelta(seconds=int(form.date.data))
            db.session.add(Event(title=form.title.data, link=form.link.data, date=date.strftime('%c')))
            db.session.commit()
        else:
            event = Event.query.filter_by(id=id).first()
            event.title=form.title.data
            event.link = form.link.data
            event.date = form.date.data
            db.session.add(event)
            db.session.commit()   
    event=Event.query.filter_by(id=id).first()
    return render_template('eventform.html', id=id, form=form, event=event, data=data)

@app.route('/dashboard/delete-event/<int:id>', methods=['GET','POST'])
@login_required
def delete_event(id):
    event = Event.query.filter_by(id=id).first()
    db.session.delete(event)
    db.session.commit()
    return redirect('/dashboard')

@app.route('/events')
def events():
    event = Event.query.all()
    return render_template('event.html', event=event)

@app.route('/articles')
def articles():
    page = request.args.get('page')
    posts = Articles.query.all()
    last = math.ceil(len(posts)/data['config']['posts_to_show'])
    if not str(page).isnumeric():
        page = 1

    page = int(page)
    posts = posts[(page-1)*data['config']['posts_to_show']:(page-1)*data['config']['posts_to_show']+data['config']['posts_to_show']]
    if page==1:
        prev = '#'
        next = f'?page={page+1}'
    elif page==last:
        prev = f'?page={page-1}'
        next = '#'
    else:
        prev = f'?page={page-1}'
        next = f'?page={page+1}'
    return render_template('article.html', posts=posts, prev=prev, next=next)

@app.route('/articles/<string:slug>')
def blogpost(slug):
    post = Articles.query.filter_by(slug=slug).first()
    return render_template('article1.html', post=post)

@app.route('/contact', methods=['GET','POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        db.session.add(Contact(email=form.email.data, subject=form.subject.data, message=form.message.data))
        db.session.commit()
    return render_template('contact.html', form=form)

@app.route('/about')
def about():
    return render_template("about.html")

if __name__=='__main__':
    app.run(debug=True)