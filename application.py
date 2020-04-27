import logging
import socket
from flask import Flask, session
from flask_session import Session
import sys
import os
import routes
from config import application
from config import db_manager
from config import config
from werkzeug.middleware.profiler import ProfilerMiddleware
from flask_cors import CORS

config.configure_app(application)
db_manager.connect(application)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

CORS(application)

# application.wsgi_app = ProfilerMiddleware(
#     application.wsgi_app)

if __name__ == "__main__":
    application.run()
