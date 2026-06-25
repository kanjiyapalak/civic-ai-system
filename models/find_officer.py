# models/officer_service.py

from models.db import officers_collection

def find_officer(department_id, ward_id):
    return officers_collection.find_one({
        "department_id": department_id,
        "ward_id": ward_id
    })