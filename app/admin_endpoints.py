import datetime

from flask import Response, request, abort
from playhouse.shortcuts import model_to_dict
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
)
from peewee import DoesNotExist

from app import app, config
from app.models import Birthdays
from app.utils import (
    _decrypt,
    admin_required,
    PubicKeyError,
    _abort_error,
)

JWT_EXPIRES_MINUTES = int(config.get("Main", "jwt_expires_minutes"))
TELEGRAM_BOT_TOKEN = str(config.get("Main", "telegram_bot_token"))


@app.route("/admin/login")
def admin_login():
    try:
        if not (_decrypt(request.args.get("encrypted_bot_id")) == TELEGRAM_BOT_TOKEN):
            abort(403, description="Access denied")

        jwt_token = create_access_token(
            identity="admin",
            expires_delta=datetime.timedelta(minutes=JWT_EXPIRES_MINUTES),
            additional_claims={"is_admin": True},
        )
        response = Response(status=200)
        set_access_cookies(response, jwt_token)
        return response
    except PubicKeyError:
        abort(422, description="Decryption failed: Invalid public key")
    except Exception as error:
        _abort_error(error)


@app.route("/birthdays/incoming", methods=["GET"])
@admin_required
def incoming_birthdays():
    try:
        datetimes = {
            datetime.date.today(): "today",  # without text
            datetime.date.today() + datetime.timedelta(days=1): "tomorrow",
            datetime.date.today() + datetime.timedelta(days=7): "week",
        }
        data = []
        for incoming_in in datetimes:
            for birthday in Birthdays.select().where(
                (Birthdays.day == incoming_in.day)
                & (Birthdays.month == incoming_in.month)
            ):
                data += (model_to_dict(birthday), model_to_dict(birthday.creator))
        return data
    except DoesNotExist:
        abort(404, description="No incoming birthdays")
    except Exception as error:
        _abort_error(error)


@app.route("/birthdays/all", methods=["GET"])
@admin_required
def all_birthdays():
    try:
        data = []
        for birthday in Birthdays.select():
            data += (model_to_dict(birthday), model_to_dict(birthday.creator))
        return data
    except DoesNotExist:
        abort(404, description="No birthdays")
    except Exception as error:
        _abort_error(error)
