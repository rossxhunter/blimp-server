from config import db_manager
from datetime import datetime
import json
import csv


def add_click(session_id, action, mode, metadata):
    timestamp = datetime.now()
    db_manager.insert("""
    INSERT INTO clicks (id, mode, action, metadata, timestamp) 
    VALUES ("{id}", "{mode}", "{action}", "{metadata}", "{timestamp}")
    """.format(action=action, id=session_id, timestamp=timestamp, metadata=metadata.replace('"', "'"), mode=mode))


def parse_clicks():
    clicks_query = db_manager.query("""
    SELECT id, action, metadata 
    FROM clicks
    WHERE mode = "evaluation"
    """)
    clicks = [{"add_activity": 0,
               "delete_activity": 0,
               "change_activities": 0,
               "change_travel_method": 0,
               "reorder_activities": 0,
               "change_duration": 0,
               "change_activities_done": 0,
               "update_window": 0
               }, {"add_activity": 0,
                   "delete_activity": 0,
                   "change_activities": 0,
                   "change_travel_method": 0,
                   "reorder_activities": 0,
                   "change_duration": 0,
                   "change_activities_done": 0,
                   "update_window": 0
                   }, {"add_activity": 0,
                       "delete_activity": 0,
                       "change_activities": 0,
                       "change_travel_method": 0,
                       "reorder_activities": 0,
                       "change_duration": 0,
                       "change_activities_done": 0,
                       "update_window": 0
                       }]
    for c in clicks_query:
        itinNum = json.loads(c[2].replace("'", '"'))["itinNum"]
        clicks[itinNum][c[1]] += 1
    with open('clicks.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["", "add_activity",
                         "delete_activity",
                         "change_activities",
                         "change_travel_method",
                         "reorder_activities",
                         "change_duration", "change_activities_done", "update_window"])
        for c in clicks:
            writer.writerow(["", c["add_activity"], c["delete_activity"],
                             c["change_activities"], c["change_travel_method"], c["reorder_activities"], c["change_duration"], c["change_activities_done"], c["update_window"]])
