import motor.motor_asyncio
from typing import List, Optional
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Aztec89:t3stP@55wOrd@cluster0.cnkgfbd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.video_compressor

admins_collection = db.admins
thumbnails_collection = db.thumbnails
settings_collection = db.settings

class Database:
    @staticmethod
    async def add_admin(user_id: int) -> bool:
        try:
            await admins_collection.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )
            return True
        except:
            return False
    
    @staticmethod
    async def remove_admin(user_id: int) -> bool:
        try:
            result = await admins_collection.delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except:
            return False
    
    @staticmethod
    async def get_admins() -> List[int]:
        try:
            admins = await admins_collection.find({}).to_list(length=None)
            return [admin["user_id"] for admin in admins]
        except:
            return []
    
    @staticmethod
    async def is_admin(user_id: int) -> bool:
        try:
            admin = await admins_collection.find_one({"user_id": user_id})
            return admin is not None
        except:
            return False
    
    @staticmethod
    async def set_thumbnail(file_id: str) -> bool:
        try:
            await thumbnails_collection.update_one(
                {"_id": "default"},
                {"$set": {"file_id": file_id}},
                upsert=True
            )
            return True
        except:
            return False
    
    @staticmethod
    async def get_thumbnail() -> Optional[str]:
        try:
            thumbnail = await thumbnails_collection.find_one({"_id": "default"})
            return thumbnail["file_id"] if thumbnail else None
        except:
            return None
    
    @staticmethod
    async def save_video_settings(settings: dict) -> bool:
        try:
            await settings_collection.update_one(
                {"_id": "video_settings"},
                {"$set": settings},
                upsert=True
            )
            return True
        except:
            return False
    
    @staticmethod
    async def load_video_settings() -> dict:
        try:
            settings = await settings_collection.find_one({"_id": "video_settings"})
            if settings:
                settings.pop("_id", None)
                return settings
            return {}
        except:
            return {}
  
