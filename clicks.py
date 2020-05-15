from config import db_manager
from datetime import datetime


def add_click(session_id, action, mode, metadata):
    timestamp = datetime.now()
    db_manager.insert("""
    INSERT INTO clicks (id, mode, action, metadata, timestamp) VALUES ("{id}", "{mode}", "{action}", "{metadata}", "{timestamp}")
    """.format(action=action, id=session_id, timestamp=timestamp, metadata=metadata.replace('"', "'"), mode=mode))
