from flask import Flask, jsonify, url_for, redirect, render_template, request, abort
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
)
from flask_login import login_required, LoginManager, login_user, UserMixin, logout_user
from playhouse.shortcuts import model_to_dict
import os
from hashlib import sha256
import hmac

app = Flask(__name__)
app.secret_key = os.urandom(16)

db = PostgresqlDatabase("postgres", user="postgres", password="postgres")

login_manager = LoginManager(app)

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel, UserMixin):
    telegram_id = CharField(unique=True)  # col_creator
    language = CharField(
        default="en"
    )  # col_language. #one lang - en, automatic translation later.


class Birthdays(BaseModel):
    name = CharField()  # col_name
    day = SmallIntegerField()  # col_day
    month = SmallIntegerField()  # col_month
    year = SmallIntegerField(null=True)  # col_year
    note = TextField(null=True)  # col_note
    creator = ForeignKeyField(User, backref="birthdays")  # col_creator


with app.app_context():
    # db.drop_tables([Birthdays, User])
    db.create_tables([Birthdays, User])


# @app.route("/login")
# def telegram_auth():
#     return render_template("login_redirect.html", title="Login")


# @app.route("/logout")
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for("telegram_auth"))


# @app.route("/webpage", methods=["GET", "POST"])
# def webpage():
#     secret_key = sha256(
#         bytes("5936456116:AAFSjRwO1TqBjwbodOxREQW3ZsWGXWvDFzA", "utf-8")
#     ).digest()
#     # secret_key = "5936456116:AAFSjRwO1TqBjwbodOxREQW3ZsWGXWvDFzA"
#     data_check_dict = request.args.to_dict()
#     del data_check_dict["hash"]
#     sorted_tuples = sorted(data_check_dict.items())
#     data_check_list = []
#     for key, value in sorted_tuples:
#         data_check_list.append(f"{key}={value}")
#     data_check_string = "\n".join(data_check_list)
#     print(data_check_string)
#     fuck = hmac.new(
#         key=secret_key,
#         msg=bytes(data_check_string, "utf-8"),
#         digestmod=sha256,
#     ).hexdigest()
#     if fuck != request.args.get("hash"):
#         return abort(403)

#     current_user = User.get(User.telegram_id == 1234)
#     login_user(current_user)
#     birthdays = User.get(User.telegram_id == 1234).birthdays
#     if birthdays:
#         return jsonify([model_to_dict(birthday) for birthday in birthdays])


@app.route("/birthdays", methods=["GET"])
def users_birthdays():
    birthdays = User.get(User.telegram_id == 1234).birthdays
    return jsonify([model_to_dict(birthday) for birthday in birthdays])


@app.route("/birthdays/<string:name>", methods=["GET"])
def one_birthday(name):
    data = request.get_json()
    birthday = User.get(User.telegram_id == 1234).birthdays.get(
        Birthdays.name == "Oleh"
    )
    print(birthday)
    return "", 200


@app.route("/birthdays", methods=["POST"])
def add_birthday():
    data = request.get_json()
    user, created = User.get_or_create(telegram_id=data.get("id"))
    Birthdays.create(
        name=data.get("name"),
        day=data.get("day"),
        month=data.get("month"),
        year=data.get("year"),
        creator=user,
    )
    return "", 201


@app.route("/birthdays/<string:name>", methods=["DELETE"])
def delete_birthday(name):
    # data = request.get_json()
    # user = User.get(telegram_id=data.get("id"))
    Birthdays.delete().where(
        (Birthdays.creator == User.get(telegram_id=1234)) & (Birthdays.name == name)
    )
    return "", 204


@app.route("/birthdays", methods=[""])
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# User.create(telegram_id=1234)

# Birthdays.create(
#     name="Oleh",
#     day=12,
#     month=4,
#     year=2003,
#     creator=User.get(User.telegram_id == 1234),
# )

# User.create(telegram_id=4321, col_language="en")

# Birthdays.create(
#     col_name="Nazar",
#     col_day=15,
#     col_month=3,
#     col_year=2002,
#     telegram_id=User.get(User.telegram_id == 4321),
# )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
