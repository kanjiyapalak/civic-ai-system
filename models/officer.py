# models/officer_model.py

from datetime import datetime

from models.db import officers_collection


def create_officer(data):
    officer = {
        "user_id": data["user_id"],
        "department_id": data["department_id"],
        "ward_id": data["ward_id"],
        "created_at": datetime.utcnow(),
    }
    return officers_collection.insert_one(officer)