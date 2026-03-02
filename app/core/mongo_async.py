from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoAsync:
    client: AsyncIOMotorClient = None

mongo_async = MongoAsync()

async def connect_to_mongo():
    mongo_async.client = AsyncIOMotorClient(settings.mongo_uri)

    # Force connection validation
    await mongo_async.client.admin.command("ping")

async def close_mongo_connection():
    mongo_async.client.close()

def get_database():
    return mongo_async.client[settings.mongo_db_name]