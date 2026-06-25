# models/ward_model.py

from models.db import wards_collection

def create_ward(data):
    ward = {
        "name": data["name"],
        "city": data["city"],
        "boundary": data["boundary"]  # polygon [[lon, lat], ...]
    }

    if "state" in data:
        ward["state"] = data["state"]
    if "country" in data:
        ward["country"] = data["country"]

    return wards_collection.insert_one(ward)

def get_all_wards():
    return list(wards_collection.find())