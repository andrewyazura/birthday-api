from flask import Flask, jsonify, url_for, redirect, render_template, request, abort
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
)
from flask_login import (
    login_required,
    LoginManager,
    login_user,
    UserMixin,
    logout_user,
    current_user,
)
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


# frontend
@app.route("/")
def telegram_login():
    return render_template("login_redirect.html", title="Login")


# frontend
@app.route("/logout")
@login_required
def logout():
    logout_user()
    # return redirect(url_for("telegram_login"))
    return "", 200


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
# @login_required
def users_birthdays():
    # data = request.get_json()
    # birthdays = User.get(User.telegram_id == data.get("id")).birthdays
    birthdays = User.get(User.telegram_id == 1234).birthdays
    return jsonify([model_to_dict(birthday) for birthday in birthdays]), 200


@app.route("/birthdays/<name>", methods=["GET"])
# @login_required
def one_birthday(name):
    # data = request.get_json()
    # user = User.get(User.telegram_id == data.get("id"))
    user = User.get(User.telegram_id == "1234")
    birthday = Birthdays.get((Birthdays.creator == user) & (Birthdays.name == name))
    return jsonify(model_to_dict(birthday)), 200


@app.route("/birthdays", methods=["POST"])
# @login_required
def add_birthday():
    data = request.get_json()
    user, created = User.get_or_create(telegram_id=data.get("id"))
    Birthdays.create(
        name=data.get("name"),
        day=data.get("day"),
        month=data.get("month"),
        year=data.get("year"),  # ignores if no year in request
        creator=user,
    )
    return data, 201


@app.route(
    "/birthdays", methods=["PATCH"]
)  # only add to existing data, request has only new data
# @login_required
def update_birthday():
    data = request.get_json()
    user = User.get(User.telegram_id == data.get("id"))
    if (
        not Birthdays.update(note=data.get("note"))
        .where((Birthdays.creator == user) & (Birthdays.name == "Vova"))
        .execute()
    ):
        return abort(404)
    return data, 201


@app.route("/birthdays/<name>", methods=["DELETE"])
def delete_birthday(name):
    # data = request.get_json()
    # user = User.get(User.telegram_id == data.get("id"))
    user = User.get(User.telegram_id == "1234")
    if (
        not Birthdays.delete()
        .where((Birthdays.creator == user) & (Birthdays.name == name))
        .execute()
    ):
        return abort(404)
    return "deleted", 204


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
#     name="Nazar",
#     day=15,
#     month=3,
#     year=2002,
#     creator=User.get(User.telegram_id == 4321),
# )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
