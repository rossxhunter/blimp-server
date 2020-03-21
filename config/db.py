from flaskext.mysql import MySQL
from flask.app import Flask


class DBManager:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self, app):
        mysql = MySQL()
        mysql.init_app(app)
        self.conn = mysql.connect()
        self.cursor = self.conn.cursor()

    def query(self, q):
        self.cursor.execute(q)
        return self.cursor.fetchall()

    def insert(self, i):
        try:
            self.cursor.execute(i)
            self.conn.commit()
            return True
        except Exception as e:
            print("Problem inserting into db: " + str(e))
            return False
