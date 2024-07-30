from app import app, config
from datetime import datetime
from flask import make_response
from werkzeug.exceptions import HTTPException
from hashlib import sha256
import hmac
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt
from flask_jwt_extended import verify_jwt_in_request


TELEGRAM_BOT_TOKEN = config.get("Main", "telegram_bot_token")


class PubicKeyError(Exception):
    pass


class CustomError(HTTPException):
    def __init__(self, status_code, description, field):
        super().__init__()
        self.code = status_code
        self.field = field
        self.description = description


@app.errorhandler(CustomError)
def handle_custom_error(e):
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
    response.headers.add("Access-Control-Allow-Headers", "X-CSRF-TOKEN, Content-Type")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,HEAD,POST,DELETE,PUT,OPTIONS"
    )
    return response


def _check_telegram_data(data_dict) -> bool:
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
    @wraps(func)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims["is_admin"]:
            return func(*args, **kwargs)
        else:
            return jsonify(msg="Admins only!"), 403

    return decorator
