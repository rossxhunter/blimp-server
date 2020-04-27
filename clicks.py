from config import db_manager


def add_new_clicks_record(session_id):
    db_manager.insert("""
    INSERT INTO clicks (id) VALUES ("{id}")
    """.format(id=session_id))


def increment_click(session_id, click):
    db_manager.insert("""
    UPDATE clicks SET {click} = {click} + 1 WHERE id = "{id}"
    """.format(click=click, id=session_id))
