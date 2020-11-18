from flask.app import Flask
from config import db

application = Flask(__name__)
db_manager = db.DBManager()
root_folder = "backend"
