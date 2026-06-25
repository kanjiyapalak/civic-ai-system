# models/department_model.py

from models.db import departments_collection

def create_department(name):
    return departments_collection.insert_one({
        "name": name
    })

def get_department_by_name(name):
    return departments_collection.find_one({"name": name})