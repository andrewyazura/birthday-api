from app import app, config
from datetime import datetime
from flask import make_response
from werkzeug.exceptions import HTTPException
from hashlib import sha256
import hmac

TELEGRAM_BOT_TOKEN = config.get("Main", "telegram_bot_token")


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
    app.logger.error(f"{datetime.now()}:  {response.get_data(as_text=True)}")
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
