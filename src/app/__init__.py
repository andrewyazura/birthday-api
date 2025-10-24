import configparser
import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

fallback_config_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")
config_file_path = os.getenv("CONFIG_FILE_PATH", fallback_config_path)

config = configparser.ConfigParser()
config.read(config_file_path)

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = config.get("Main", "secret_key")
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]

jwt = JWTManager(app)

CORS(app)
