from flask.app import Flask
from config import db

application = Flask(__name__)
dbManager = db.DBManager()
