# models/notification_model.py

from models.db import notifications_collection
from datetime import datetime

def create_notification(complaint_id, officer_id):
    notification = {
        "complaint_id": complaint_id,
        "officer_id": officer_id,

        "status": "SENT",
        "retry_count": 0,
        "last_sent_at": datetime.utcnow()
    }

    return notifications_collection.insert_one(notification)