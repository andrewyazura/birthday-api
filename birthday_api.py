from flask import Flask, jsonify, url_for, redirect, render_template
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
)
from flask_login import login_required, LoginManager
from playhouse.shortcuts import model_to_dict
import os


app = Flask(__name__)

db = PostgresqlDatabase("postgres", user="postgres", password="postgres")

login_manager = LoginManager(app)

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    col_creator = CharField()
    col_language = CharField(default="en")


class Birthdays(BaseModel):
    col_name = CharField()
    col_day = SmallIntegerField()
    col_month = SmallIntegerField()
    col_year = SmallIntegerField(null=True)
    col_note = TextField(null=True)
    col_creator = ForeignKeyField(User, backref="birthdays")


with app.app_context():
    # db.drop_tables([Birthdays, User])
    db.create_tables([Birthdays, User])


@app.route("/login", methods=["GET", "POST"])
def telegram_auth():
    return render_template("login_redirect.html", title="Login")


@app.route("/webpage", methods=["GET"])
def webpage():
    birthdays = User.get(User.col_creator == 1234).birthdays
    return jsonify([model_to_dict(birthday) for birthday in birthdays])


@app.route("/birthdays", methods=["GET"])
# @login_required
def users_birthdays():
    birthdays = User.get(User.col_creator == 1234).birthdays
    return jsonify([model_to_dict(birthday) for birthday in birthdays])


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# User.create(col_creator=1234, col_language="en")

# Birthdays.create(
#     col_name="Oleh",
#     col_day=12,
#     col_month=4,
#     col_year=2003,
#     col_creator=User.get(User.col_creator == 1234),
# )

# User.create(col_creator=4321, col_language="en")

# Birthdays.create(
#     col_name="Nazar",
#     col_day=15,
#     col_month=3,
#     col_year=2002,
#     col_creator=User.get(User.col_creator == 4321),
# )
