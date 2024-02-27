from app import app, config
from app.models import Users, Birthdays, birthdays_schema
from app.utils import _check_telegram_data
from flask import jsonify, Response, request, abort
from playhouse.shortcuts import model_to_dict
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from datetime import timedelta
from marshmallow import ValidationError
from peewee import DoesNotExist, IntegrityError

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
            expires_delta=timedelta(minutes=JWT_EXPIRES_MINUTES),
        )
        response = Response(status=200)
        set_access_cookies(response, jwt_token)
        return response
    except Exception as error:
        abort(500, description=f"Unexpected {error=}")


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
