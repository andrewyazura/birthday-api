from flask import Flask
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
)
from flask_login import login_required


app = Flask(__name__)

db = PostgresqlDatabase(name="postgres", user="postgres", password="postgres")


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


with app.app_context:
    db.create_tables([Birthdays, User])


@app.route("/", methods=["GET"])
# telegram login for web


@app.route("/birthdays", methods=["GET"])
@login_required
def users_birthdays(telegram_id):
    return User.birthdays
