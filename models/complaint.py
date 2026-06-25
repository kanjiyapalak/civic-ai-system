# models/complaint_model.py

from models.db import complaints_collection
from datetime import datetime

def create_complaint(data):
    complaint = {
        "user_id": data["user_id"],
        "description": data["description"],

        "issue_type": None,
        "department_id": None,
        "ward_id": None,
        "officer_id": None,

        "status": "PENDING",

        "is_duplicate": False,
        "parent_complaint_id": None,

        "is_resolved": False,

        "location": {
            "lat": data["lat"],
            "lon": data["lon"]
        },

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    return complaints_collection.insert_one(complaint)