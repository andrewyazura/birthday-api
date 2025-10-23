"""Routes for basic usage of the API"""

import datetime
import logging

from flask import Response, abort, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from marshmallow import ValidationError
from peewee import DoesNotExist, IntegrityError
from playhouse.shortcuts import model_to_dict

from src.app import app, config
from src.app.models import Birthdays, Users, birthdays_schema
from src.app.utils import (
    CustomError,
    PubicKeyError,
    _abort_error,
    _check_telegram_data,
    _decrypt,
)

JWT_EXPIRES_MINUTES = int(config.get("Main", "jwt_expires_minutes"))
TELEGRAM_BOT_TOKEN = str(config.get("Main", "telegram_bot_token"))


@app.route("/public-key")
def public_key():
    """Return the public key for the client

    This key is for encrypting the bot token before sending it to the server
    """
    try:
        with open(config.get("Keys", "public"), "rb") as f:
            pem = f.read()

        pem_str = pem.decode("utf-8")
        logging.info("Public key sent")

        return jsonify({"public_key": pem_str})

    except Exception as error:
        logging.error(f"Request: {request} Error: {error}")
        _abort_error(error)


@app.route("/login")
def user_login():
    """Login endpoint for the user

    Request args should have user's id and either bot's encrypted id or data from telegram's login widget

    Returns a JWT token in cookies, should be used for further requests.
    Also CSRF token should be manually set in headers for further requests
    """
    try:
        logging.info(f"Login request received with args: {request.args.to_dict()}")

        if request.args.get("encrypted_bot_id"):
            logging.info("Decrypting bot id")
            received_bot_token = _decrypt(request.args.get("encrypted_bot_id"))
            if received_bot_token != TELEGRAM_BOT_TOKEN:
                logging.warning(f"Invalid bot id: {received_bot_token}")
                abort(403, description="Invalid bot id")
        elif not _check_telegram_data(request.args.to_dict()):
            logging.warning(
                f"Telegram data validation failed. Request.args: {request.args.to_dict()}"
            )
            abort(412, description="Bad credentials")

        user, created = Users.get_or_create(telegram_id=request.args.get("id"))
        if created:
            logging.info(f"New user created with telegram_id: {user.telegram_id}")

        identity = {"telegram_id": user.telegram_id}
        jwt_token = create_access_token(
            identity=identity,
            expires_delta=datetime.timedelta(minutes=JWT_EXPIRES_MINUTES),
        )

        response = Response(status=200)
        set_access_cookies(response, jwt_token)
        logging.info(
            f"JWT token generated and cookies set for telegram_id: {user.telegram_id}"
        )
        return response
    except PubicKeyError:
        logging.error("Decryption failed: Invalid public key")
        abort(422, description="Decryption failed: Invalid public key")
    except Exception as error:
        logging.error(f"Request: {request.args.to_dict()} Error: {error}")
        _abort_error(error)


@app.route("/logout")
@jwt_required()
def logout():
    """Logout endpoint for the user"""
    try:
        response = Response(status=200)
        unset_jwt_cookies(response)
        logging.info("JWT cookies unset")
        return response
    except Exception as error:
        logging.error(f"Error during logout: {error}")
        _abort_error(error)


@app.route("/birthdays", methods=["GET"])
@jwt_required()
def users_birthdays():
    """Get all birthdays of the user"""
    try:
        current_user = get_jwt_identity()
        logging.info(
            f"Fetching birthdays for user with telegram_id: {current_user['telegram_id']}"
        )

        user = Users.get(telegram_id=current_user["telegram_id"])
        birthdays = Users.get(Users.telegram_id == user.telegram_id).birthdays

        data = [model_to_dict(birthday) for birthday in birthdays]
        if not data:
            logging.warning(
                f"No birthdays found for user with telegram_id: {current_user['telegram_id']}"
            )
            abort(404, description="There are no birthdays for this user")

        logging.info(
            f"Found {len(data)} birthdays for user with telegram_id: {current_user['telegram_id']}"
        )
        return jsonify(data), 200
    except Exception as error:
        logging.error(
            f"Error fetching birthdays for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        _abort_error(error)


@app.route("/birthdays/<int:id>", methods=["GET"])
@jwt_required()
def one_birthday(id):
    """Get one birthday of the user by id"""
    try:
        current_user = get_jwt_identity()
        logging.info(
            f"Fetching birthday with id {id} for user with telegram_id: {current_user['telegram_id']}"
        )

        user = Users.get(telegram_id=current_user["telegram_id"])
        birthday = Birthdays.get((Birthdays.creator == user) & (Birthdays.id == id))

        logging.info(
            f"Birthday with id {id} found for user with telegram_id: {current_user['telegram_id']}"
        )
        return jsonify(model_to_dict(birthday)), 200
    except DoesNotExist:
        logging.warning(
            f"Birthday with id {id} not found for user with telegram_id: {current_user['telegram_id']}"
        )
        abort(404, description="Birthday not found")
    except Exception as error:
        logging.error(
            f"Error fetching birthday with id {id} for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        _abort_error(error)


@app.route("/birthdays", methods=["POST"])
@jwt_required()
def add_birthday():
    """Add a new birthday for the user

    Request should have a JSON with the following fields:
    - name: `str`
    - day: `int`
    - month: `int`
    - year: `int`, optional, can be `Null`
    - note: `str`, optional, can be `Null`

    Returns the added birthday with its id
    """
    try:
        data = birthdays_schema.load(request.get_json())
        current_user = get_jwt_identity()
        logging.info(
            f"Adding birthday for user with telegram_id: {current_user['telegram_id']}, Data: {data}"
        )

        user = Users.get(telegram_id=current_user["telegram_id"])
        birthday_id = Birthdays.create(
            name=data.get("name"),
            day=data.get("day"),
            month=data.get("month"),
            year=data.get("year"),
            note=data.get("note"),
            creator=user,
        )

        logging.info(
            f"Birthday with id {birthday_id} added for user with telegram_id: {current_user['telegram_id']}"
        )
        response = jsonify(model_to_dict(Birthdays.get_by_id(birthday_id)))
        return response, 201
    except ValidationError as error:
        logging.warning(
            f"Validation error adding birthday for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        try:
            raise CustomError(
                422, description="\n".join(error.messages_dict["_schema"]), field="date"
            )
        except KeyError:
            abort(422, description="Unprocessable birthday data")
    except IntegrityError:
        logging.warning(
            f"Integrity error: User with telegram_id: {current_user['telegram_id']} already has a birthday with this name"
        )
        raise CustomError(
            422, description="User already has a birthday with this name", field="name"
        )
    except Exception as error:
        logging.error(
            f"Error adding birthday for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        _abort_error(error)


@app.route("/birthdays/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_birthday(id):
    """Delete a birthday by id"""
    try:
        current_user = get_jwt_identity()
        logging.info(
            f"Deleting birthday with id {id} for user with telegram_id: {current_user['telegram_id']}"
        )

        user = Users.get(telegram_id=current_user["telegram_id"])
        Birthdays.get(
            (Birthdays.creator == user) & (Birthdays.id == id)
        ).delete_instance()

        logging.info(
            f"Birthday with id {id} deleted for user with telegram_id: {current_user['telegram_id']}"
        )
        return Response(status=204)
    except DoesNotExist:
        logging.warning(
            f"Attempted to delete non-existent birthday with id {id} for user with telegram_id: {current_user['telegram_id']}"
        )
        abort(404, description="Can't delete non-existent birthday")
    except Exception as error:
        logging.error(
            f"Error deleting birthday with id {id} for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        _abort_error(error)


@app.route("/birthdays/<int:id>", methods=["PUT"])
@jwt_required()
def update_birthday(id):
    """Rewrite a birthday by id

    Request should have a JSON with the following fields:
    - name: `str`
    - day: `int`
    - month: `int`
    - year: `int`, optional, can be `Null`
    - note: `str`, optional, can be `Null`

    Returns the updated birthday with its id
    """
    try:
        data = birthdays_schema.load(request.get_json())
        current_user = get_jwt_identity()
        logging.info(
            f"Updating birthday with id {id} for user with telegram_id: {current_user['telegram_id']}, Data: {data}"
        )

        user = Users.get(telegram_id=current_user["telegram_id"])
        Birthdays.update(
            name=data.get("name"),
            day=data.get("day"),
            month=data.get("month"),
            year=data.get("year"),
            note=data.get("note"),
        ).where((Birthdays.creator == user) & (Birthdays.id == id)).execute()

        logging.info(
            f"Birthday with id {id} updated for user with telegram_id: {current_user['telegram_id']}"
        )
        response = jsonify(model_to_dict(Birthdays.get_by_id(id)))
        return response, 200
    except ValidationError as error:
        logging.warning(
            f"Validation error updating birthday with id {id} for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        try:
            raise CustomError(
                422, description="\n".join(error.messages_dict["_schema"]), field="date"
            )
        except KeyError:
            abort(422, description="Unprocessable birthday data")
    except IntegrityError:
        logging.warning(
            f"Integrity error: User with telegram_id: {current_user['telegram_id']} already has a birthday with this name"
        )
        raise CustomError(
            422, description="User already has a birthday with this name", field="name"
        )
    except DoesNotExist:
        logging.warning(
            f"Attempted to update non-existent birthday with id {id} for user with telegram_id: {current_user['telegram_id']}"
        )
        abort(404, description="Can't update non-existent birthday")
    except Exception as error:
        logging.error(
            f"Error updating birthday with id {id} for user with telegram_id: {current_user['telegram_id']}, Error: {error}"
        )
        _abort_error(error)
