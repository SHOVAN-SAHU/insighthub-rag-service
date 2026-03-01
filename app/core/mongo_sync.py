from pymongo import MongoClient
from app.core.config import settings

class MongoSync:
    client: MongoClient = None

mongo_sync = MongoSync()

def connect_to_mongo():
    mongo_sync.client = MongoClient(settings.mongo_uri)

def close_mongo_connection():
    if mongo_sync.client:
        mongo_sync.client.close()

def get_database():
    return mongo_sync.client[settings.mongo_db_name]