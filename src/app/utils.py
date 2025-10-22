"""Different helper functions, classes and decorators"""

from datetime import datetime
import hmac
import base64

from flask import make_response, jsonify, abort
from flask_jwt_extended import get_jwt
from flask_jwt_extended import verify_jwt_in_request
from werkzeug.exceptions import HTTPException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from hashlib import sha256
from functools import wraps

from app import app, config

TELEGRAM_BOT_TOKEN = config.get("Main", "telegram_bot_token")


class PubicKeyError(Exception):
    """Raised when public key is invalid"""

    pass


class CustomError(HTTPException):
    """Custom error class for handling exceptions

    Extends HTTPException class
    """

    def __init__(self, status_code, description, field):
        super().__init__()
        self.code = status_code
        self.field = field
        self.description = description


@app.errorhandler(CustomError)
def handle_custom_error(e):
    """Error handler for CustomError class

    Unlike general_exception_handler, has `field` in response
    """
    response = make_response(
        {
            "field": e.field,
            "name": e.name,
            "description": e.description,
        },
        e.code,
    )
    response.content_type = "application/json"
    app.logger.error(f"{datetime.now()}:  {response.get_data(as_text=True)}")
    return response


@app.errorhandler(HTTPException)
def general_exception_handler(e):
    """General error handler for HTTPException class"""
    response = make_response(
        {
            "name": e.name,
            "description": e.description,
        },
        e.code,
    )
    response.content_type = "application/json"
    app.logger.error(f"{datetime.now()}:  {response.get_data(as_text=True)}")
    return response


@app.after_request
def add_header(response):
    """Add headers before sending response"""
    response.headers.add("Access-Control-Allow-Headers", "X-CSRF-TOKEN, Content-Type")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,HEAD,POST,DELETE,PUT,OPTIONS"
    )
    return response


def _check_telegram_data(data_dict) -> bool:
    """Check if data from Telegram is valid

    Logic description can be found [here](https://core.telegram.org/widgets/login#checking-authorization)
    """
    try:
        secret_key = sha256(bytes(TELEGRAM_BOT_TOKEN, "utf-8")).digest()
        hash = data_dict.pop("hash")
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
    except Exception:
        return False


def _decrypt(data):
    """Decrypt data using private key"""
    encrypted_data = base64.b64decode(data)

    with open("private_key.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

    try:
        decrypted_data = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except ValueError:
        raise PubicKeyError

    return decrypted_data.decode("utf-8")


def admin_required(func):
    """Decorator for admin only endpoints"""

    @wraps(func)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims["is_admin"]:
            return func(*args, **kwargs)
        else:
            return jsonify(msg="Admins only!"), 403

    return decorator


def _abort_error(error):
    """Abort with error message

    If error is HTTPException, abort with error code and description.
    Otherwise, abort with 500 and error message.
    """
    if isinstance(error, HTTPException):
        abort(error.code, description=error.description)
    else:
        abort(500, description=f"Unexpected {error=}")
