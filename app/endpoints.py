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
    identity = {"telegram_id": user.telegram_id, "admin": "False"}
    jwt_token = create_access_token(
        identity=identity, expires_delta=datetime.timedelta(minutes=15)
    )
    response = Response(
        status=200, headers=[("Access-Control-Allow-Credentials", "true")]
    )
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
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,HEAD,POST,DELETE,PUT,OPTIONS"
    )
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


@app.route("/birthdays/<name>", methods=["OPTIONS"])
@jwt_required()
def options_birthdays_pos(name):
    return _build_cors_preflight_response()


@app.route("/birthdays", methods=["OPTIONS"])
@jwt_required()
def options_birthdays():
    return _build_cors_preflight_response()


@app.route("/birthdays", methods=["GET"])
@jwt_required()
def users_birthdays():
    current_user = get_jwt_identity()
    user = Users.get(telegram_id=current_user["telegram_id"])
    birthdays = Users.get(Users.telegram_id == user.telegram_id).birthdays
    response = jsonify([model_to_dict(birthday) for birthday in birthdays])
    response.headers.add("Access-Control-Allow-Credentials", "true")
    # response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1")
    return response


@app.route("/birthdays/<id>", methods=["GET"])
@jwt_required()
def one_birthday(id):
    current_user = get_jwt_identity()
    user, created = Users.get_or_create(telegram_id=current_user["telegram_id"])
    birthday = Birthdays.get((Birthdays.creator == user) & (Birthdays.id == id))
    return jsonify(model_to_dict(birthday))


@app.route("/birthdays", methods=["POST"])  # handle errors
@jwt_required()
def add_birthday():
    current_user = get_jwt_identity()
    user = Users.get(telegram_id=current_user["telegram_id"])
    data = request.get_json()
    # add my own birthday for every new user:) if so, its better to make another request from frontend/bot
    birthday_id = Birthdays.create(
        name=data.get("name"),
        day=data.get("day"),
        month=data.get("month"),
        year=data.get("year"),  # none if no year in request
        note=data.get("note"),  # none if no note in request
        creator=user,
    )
    response = jsonify(model_to_dict(Birthdays.get_by_id(birthday_id)))
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response, 201


@app.route("/birthdays/<id>", methods=["DELETE"])
@jwt_required()
def delete_birthday(id):
    current_user = get_jwt_identity()
    user = Users.get(telegram_id=current_user["telegram_id"])
    if (
        not Birthdays.delete()
        .where((Birthdays.creator == user) & (Birthdays.id == id))
        .execute()
    ):
        response = Response(status=404)
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response
    response = Response(status=204)
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


@app.route(
    "/birthdays/<id>",
    methods=["PUT"],  # PATCH contains only new info, PUT - new object to replace with
)  # only add to existing data, request has only new data
@jwt_required()
def update_birthday(id):
    data = request.get_json()
    current_user = get_jwt_identity()
    user, created = Users.get_or_create(telegram_id=current_user["telegram_id"])
    if created:
        response = jsonify({"msg": "new user has no birthdays to edit"})
        return response, 404
    if (
        not Birthdays.update(
            name=data.get("name"),
            note=data.get("note"),
            day=data.get("day"),
            month=data.get("month"),
            year=data.get("year"),
        )
        .where((Birthdays.creator == user) & (Birthdays.id == id))
        .execute()
    ):
        return 404
    return data, 201
