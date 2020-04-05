from flaskext.mysql import MySQL
from flask.app import Flask


class DBManager:
    def __init__(self):
        self.conn = None
        self.mysql = MySQL()

    def connect(self, app):
        self.mysql.init_app(app)
        self.open_connection()

    def open_connection(self):
        self.conn = self.mysql.connect()

    def query(self, q):
        if not self.conn.open:
            self.open_connection()
        cursor = self.conn.cursor()
        cursor.execute(q)
        result = cursor.fetchall()
        cursor.close()
        return result

    def insert(self, i):
        if not self.conn.open:
            self.open_connection()
        try:
            cursor = self.conn.cursor()
            cursor.execute(i)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print("Problem inserting into db: " + str(e))
            return False
