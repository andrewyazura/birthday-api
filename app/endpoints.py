from app import app, config
from app.models import Users, Birthdays, birthdays_schema
from flask import jsonify, Response, request, make_response, abort
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
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from peewee import DoesNotExist, IntegrityError

TELEGRAM_BOT_TOKEN = config.get("Main", "telegram_bot_token")
JWT_EXPIRES_MINUTES = int(config.get("Main", "jwt_expires_minutes"))


@app.route("/login")
def telegram_login():
    if not _check_telegram_data(request.args.to_dict()):
        abort(412, description="Bad credentials from login via Telegram")
    try:
        user, created = Users.get_or_create(telegram_id=request.args.get("id"))
        identity = {
            "telegram_id": user.telegram_id
        }  # incoming birthdays endpoint will check if telegram_id is in the config["Admins"]
        jwt_token = create_access_token(
            identity=identity,
            expires_delta=datetime.timedelta(minutes=JWT_EXPIRES_MINUTES),
        )
        response = Response(status=200)
        set_access_cookies(response, jwt_token)
        return response
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


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
    response = Response(status=200)
    unset_jwt_cookies(response)
    return response


@app.route("/birthdays", methods=["GET"])
@jwt_required()
def users_birthdays():
    try:
        current_user = get_jwt_identity()
        user = Users.get(telegram_id=current_user["telegram_id"])
        birthdays = Users.get(Users.telegram_id == user.telegram_id).birthdays
        data = [model_to_dict(birthday) for birthday in birthdays]
        if data == []:
            raise DoesNotExist
        return jsonify(data), 200
    except DoesNotExist:
        abort(404, description="There are no birthdays for this user")
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


@app.route("/birthdays/<int:id>", methods=["GET"])
@jwt_required()
def one_birthday(id):
    try:
        current_user = get_jwt_identity()
        user = Users.get(telegram_id=current_user["telegram_id"])
        birthday = Birthdays.get((Birthdays.creator == user) & (Birthdays.id == id))
        return jsonify(model_to_dict(birthday)), 200
    except DoesNotExist:
        abort(404, description="Birthday not found")
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


@app.route("/birthdays", methods=["POST"])
@jwt_required()
def add_birthday():
    try:
        data = birthdays_schema.load(request.get_json())
        current_user = get_jwt_identity()
        user = Users.get(telegram_id=current_user["telegram_id"])
        # add my own birthday for every new user:) if so, its better to make another request from frontend/bot
        birthday_id = Birthdays.create(
            name=data.get("name"),
            day=data.get("day"),
            month=data.get("month"),
            year=data.get("year"),  # .get() returns none if no key in dict
            note=data.get("note"),
            creator=user,
        )
        response = jsonify(model_to_dict(Birthdays.get_by_id(birthday_id)))
        return response, 201
    except ValidationError as error:
        print(error.messages)
        abort(422, description=error.messages)
    except IntegrityError:
        abort(422, description="User already has a birthday with this name")
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


@app.route("/birthdays/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_birthday(id):
    try:
        current_user = get_jwt_identity()
        user = Users.get(telegram_id=current_user["telegram_id"])
        Birthdays.get(
            (Birthdays.creator == user) & (Birthdays.id == id)
        ).delete_instance()
        return Response(status=204)
    except DoesNotExist:
        abort(404, description="Can't delete non-existent birthday")
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


@app.route(
    "/birthdays/<int:id>", methods=["PUT"]
)  # PATCH contains only new info, PUT - new object to replace with
@jwt_required()
def update_birthday(id):
    try:
        data = birthdays_schema.load(request.get_json())
        current_user = get_jwt_identity()
        user = Users.get(telegram_id=current_user["telegram_id"])
        Birthdays.update(
            name=data.get("name"),
            day=data.get("day"),
            month=data.get("month"),
            year=data.get("year"),
            note=data.get("note"),
        ).where((Birthdays.creator == user) & (Birthdays.id == id)).execute()
        response = jsonify(
            model_to_dict(Birthdays.get_by_id(id))
        )  # comes without id - response with id
        return response, 200
    except ValidationError as error:
        abort(422, description=error.messages)
    except DoesNotExist:
        abort(404, description="Can't update non-existent birthday")
    except IntegrityError:
        abort(422, description="User already has a birthday with this name")
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


@app.errorhandler(HTTPException)
def general_exception_handler(e):
    response = make_response(
        {
            "status": "error",
            "code": e.code,
            "name": e.name,
            "description": e.description,
        },
        e.code,
    )
    response.content_type = "application/json"
    app.logger.error(f"{datetime.datetime.now()}:  {response.get_data(as_text=True)}")
    return response


@app.after_request
def add_header(response):
    # response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1")
    response.headers.add("Access-Control-Allow-Headers", "X-CSRF-TOKEN, Content-Type")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,HEAD,POST,DELETE,PUT,OPTIONS"
    )
    return response
