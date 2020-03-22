import os


def configure_app(app):
    app.config['MYSQL_DATABASE_USER'] = os.environ['MYSQL_DATABASE_USER']
    app.config['MYSQL_DATABASE_PASSWORD'] = os.environ['MYSQL_DATABASE_PASSWORD']
    app.config['MYSQL_DATABASE_DB'] = os.environ['MYSQL_DATABASE_DB']
    app.config['MYSQL_DATABASE_HOST'] = os.environ['MYSQL_DATABASE_HOST']
    # app.config['MYSQL_DATABASE_SOCKET'] = os.environ['MYSQL_DATABASE_SOCKET']
    app.config['PROFILE'] = True
