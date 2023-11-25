from flask import (
    Flask,
    jsonify,
    url_for,
    redirect,
    render_template,
    abort,
    Response,
    request,
    make_response,
)
from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    SmallIntegerField,
    CharField,
    ForeignKeyField,
)
from playhouse.shortcuts import model_to_dict
import os
from hashlib import sha256
import hmac
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    JWTManager,
    set_access_cookies,
    unset_jwt_cookies,
)
import configparser
import datetime
import json
from flask_cors import CORS

# os.chdir(os.path.dirname(os.path.abspath(__file__))) #set file's directory as working
config = configparser.ConfigParser()
config.read("config.ini")

app = Flask(__name__)
CORS(
    app,
    allow_headers=["X-CSRF-TOKEN"],
    supports_credentials=True,
    origins="http://127.0.0.1",
)

app.config["JWT_SECRET_KEY"] = config.get("Main", "secret_key")
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
TELEGRAM_BOT_TOKEN = config.get("Main", "telegram_bot_token")
# app.config["JWT_COOKIE_SECURE"] = False

db = PostgresqlDatabase("postgres", user="postgres", password="postgres")


# basedir = os.path.abspath(os.path.dirname(__file__))

# JWT_SECRET_KEY = config.get("Main", "secret_key")  # Change this!
jwt = JWTManager(app)

cors = CORS(app)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
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


@app.route("/login")
def telegram_login():
    # data = check_telegram_data(request.args.to_dict())
    if not check_telegram_data(request.args.to_dict()):
        return 412
    user, created = User.get_or_create(
        telegram_id=request.args.get("id")
    )  # not sure it gets request data right
    identity = json.dumps({"telegram_id": user.telegram_id, "admin": "False"})
    jwt_token = create_access_token(
        identity=identity, expires_delta=datetime.timedelta(minutes=15)
    )
    response = Response(status=200)
    response.headers.add(
    "Access-Control-Allow-Origin", "http://127.0.0.1"
    )  # http://127.0.0.1
    response.headers.add("Access-Control-Allow-Credentials", "true")
    # response.set_cookie("jwt", value=jwt_token, httponly=True)
    set_access_cookies(response, jwt_token)  # domain="127.0.0.1"
    # access-control-expose-headers: Set-Cookie
    print("finish")
    return response


def check_telegram_data(data_dict):
    secret_key = sha256(bytes(TELEGRAM_BOT_TOKEN, "utf-8")).digest()
    hash = data_dict["hash"]
    del data_dict["hash"]
    sorted_tuples = sorted(data_dict.items())
    data_list = []
    for key, value in sorted_tuples:
        data_list.append(f"{key}={value}")
    data_string = "\n".join(data_list)
    hash_compose = hmac.new(
        key=secret_key,
        msg=bytes(data_string, "utf-8"),
        digestmod=sha256,
    ).hexdigest()
    return hash_compose == hash


@app.route("/logout")
@jwt_required()
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response


def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1")
    response.headers.add("Access-Control-Allow-Headers", "X-CSRF-TOKEN")
    response.headers.add("Access-Control-Allow-Methods", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


@app.route("/birthdays", methods=["GET", "OPTIONS"])
@jwt_required()
def users_birthdays():
    print("went into birthdays endpoint")
    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_preflight_response()
    # print(get_jwt_identity())
    # current_user = (
    #     get_jwt_identity()
    # )  # equals to telegram_id (identity when creating token)
    birthdays = User.get(User.telegram_id == 1234).birthdays
    # data = request.get_json()
    # birthdays = User.get(User.telegram_id == data.get("id")).birthdays
    response = jsonify([model_to_dict(birthday) for birthday in birthdays])
    # response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


# @app.route("/birthdays/<name>", methods=["GET"])
# # @jwt_required()
# def one_birthday(name):
#     # data = request.get_json()
#     # user = User.get(User.telegram_id == data.get("id"))
#     user = User.get(User.telegram_id == "1234")
#     birthday = Birthdays.get((Birthdays.creator == user) & (Birthdays.name == name))
#     return jsonify(model_to_dict(birthday)), 200


# @app.route("/birthdays", methods=["POST"])
# # @jwt_required()
# def add_birthday():
#     data = request.get_json()
#     user, created = User.get_or_create(telegram_id=data.get("id"))
#     Birthdays.create(
#         name=data.get("name"),
#         day=data.get("day"),
#         month=data.get("month"),
#         year=data.get("year"),  # ignores if no year in request
#         creator=user,
#     )
#     return data, 201


# @app.route(
#     "/birthdays", methods=["PATCH"]
# )  # only add to existing data, request has only new data
# # @jwt_required()
# def update_birthday():
#     data = request.get_json()
#     user = User.get(User.telegram_id == data.get("id"))
#     if (
#         not Birthdays.update(note=data.get("note"))
#         .where((Birthdays.creator == user) & (Birthdays.name == "Vova"))
#         .execute()
#     ):
#         return abort(404)
#     return data, 201


# @app.route("/birthdays/<name>", methods=["DELETE"])
# def delete_birthday(name):
#     # data = request.get_json()
#     # user = User.get(User.telegram_id == data.get("id"))
#     user = User.get(User.telegram_id == "1234")
#     if (
#         not Birthdays.delete()
#         .where((Birthdays.creator == user) & (Birthdays.name == name))
#         .execute()
#     ):
#         return abort(404)
#     return "deleted", 204


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
#     data_string = "\n".join(data_check_list)
#     print(data_string)
#     fuck = hmac.new(
#         key=secret_key,
#         msg=bytes(data_string, "utf-8"),
#         digestmod=sha256,
#     ).hexdigest()
#     if fuck != request.args.get("hash"):
#         return abort(403)

#     current_user = User.get(User.telegram_id == 1234)
#     login_user(current_user)
#     birthdays = User.get(User.telegram_id == 1234).birthdays
#     if birthdays:
#         return jsonify([model_to_dict(birthday) for birthday in birthdays])

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
    app.run(host="127.0.0.1", port=8080, debug=True)