from flask import Flask
from flask_jwt_extended import JWTManager
import configparser
from flask_cors import CORS
import logging 


# os.chdir(os.path.dirname(os.path.abspath(__file__))) #set file's directory as working
config = configparser.ConfigParser()
config.read("config.ini")

app = Flask(__name__)

app.logger.setLevel(logging.WARNING)
handler = logging.FileHandler('app.log')
app.logger.addHandler(handler)


app.config["JWT_SECRET_KEY"] = config.get("Main", "secret_key")
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]

jwt = JWTManager(app)

CORS(app)
# CORS(
#     app,
#     supports_credentials=True,
#     allow_headers=["X-CSRF-TOKEN"],
#     origins="http://127.0.0.1",
# )
