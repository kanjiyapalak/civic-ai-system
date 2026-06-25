# models/complaint_image_model.py

from models.db import images_collection
from datetime import datetime

def add_image(data):
    image = {
        "complaint_id": data["complaint_id"],
        "image_url": data["image_url"],
        "type": data["type"],  # BEFORE / AFTER

        "location": {
            "lat": data["lat"],
            "lon": data["lon"]
        },

        "created_at": datetime.utcnow()
    }

    return images_collection.insert_one(image)