from app import app, config
from app.models import Users, Birthdays
from flask import (
    jsonify,
    Response,
    request,
    make_response,
)
from playhouse.shortcuts import model_to_dict
from hashlib import sha256
import hmac
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
import datetime

TELEGRAM_BOT_TOKEN = config.get("Main", "telegram_bot_token")


@app.route("/login")
def telegram_login():
    if not _check_telegram_data(request.args.to_dict()):
        return 412
    user, created = Users.get_or_create(telegram_id=request.args.get("id"))
    print(user.telegram_id, created)
    identity = {"telegram_id": user.telegram_id, "admin": "False"}
    jwt_token = create_access_token(
        identity=identity, expires_delta=datetime.timedelta(minutes=15)
    )
    response = Response(status=200)
    response.headers.add("Access-Control-Allow-Credentials", "true")
    set_access_cookies(response, jwt_token)
    return response


def _check_telegram_data(data_dict):
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
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    current_user = get_jwt_identity()
    print(current_user["telegram_id"])
    birthdays = Users.get(Users.telegram_id == current_user["telegram_id"]).birthdays
    response = jsonify([model_to_dict(birthday) for birthday in birthdays])
    # response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


@app.route("/birthdays/<name>", methods=["GET"])
@jwt_required()
def one_birthday(name):
    current_user = get_jwt_identity()
    birthday = Birthdays.get(
        (Birthdays.creator == current_user["telegram_id"]) & (Birthdays.name == name)
    )
    return jsonify(model_to_dict(birthday))


# @app.route("/birthdays", methods=["POST"])
# # @jwt_required()
# def add_birthday():
#     data = request.get_json()
#     user, created = Users.get_or_create(telegram_id=data.get("id"))
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
#     user = Users.get(User.telegram_id == data.get("id"))
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
#     # user = Users.get(Users.telegram_id == data.get("id"))
#     user = Users.get(Users.telegram_id == "1234")
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
