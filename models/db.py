# models/db.py

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]


def ensure_collections_exist():
	expected_collections = [
		"users",
		"departments",
		"wards",
		"officers",
		"complaints",
		"complaint_images",
		"notifications",
	]
	existing_collections = set(db.list_collection_names())

	for collection_name in expected_collections:
		if collection_name not in existing_collections:
			db.create_collection(collection_name)


ensure_collections_exist()

users_collection = db["users"]
departments_collection = db["departments"]
wards_collection = db["wards"]
officers_collection = db["officers"]
complaints_collection = db["complaints"]
images_collection = db["complaint_images"]
notifications_collection = db["notifications"]