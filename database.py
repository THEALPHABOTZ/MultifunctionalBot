import motor.motor_asyncio
from typing import List, Optional
import os
import urllib.parse

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Aztec89:t3stP@55wOrd@cluster0.cnkgfbd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

def encode_mongo_uri(uri: str) -> str:
    if not uri:
        return ""
    
    if "://" not in uri:
        return uri
        
    try:
        parts = uri.split("://")
        protocol = parts[0]
        rest = parts[1]
        
        if "@" in rest:
            auth_part, host_part = rest.split("@", 1)
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)
                encoded_username = urllib.parse.quote_plus(username)
                encoded_password = urllib.parse.quote_plus(password)
                encoded_uri = f"{protocol}://{encoded_username}:{encoded_password}@{host_part}"
                return encoded_uri
    except:
        pass
    
    return uri

encoded_uri = encode_mongo_uri(MONGO_URI)
client = motor.motor_asyncio.AsyncIOMotorClient(encoded_uri)
db = client.video_compressor

admins_collection = db.admins
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

class LocalThumbnail:
    def __init__(self):
        self.thumbnail_dir = os.path.join(os.getcwd(), "thumbnails")
        self.thumbnail_path = os.path.join(self.thumbnail_dir, "custom_thumbnail.jpg")
        os.makedirs(self.thumbnail_dir, exist_ok=True)
    
    async def set_thumbnail(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                import shutil
                shutil.copy2(file_path, self.thumbnail_path)
                return True
            return False
        except:
            return False
    
    async def get_thumbnail(self) -> Optional[str]:
        try:
            if os.path.exists(self.thumbnail_path):
                return self.thumbnail_path
            return None
        except:
            return None
    
    async def has_thumbnail(self) -> bool:
        return os.path.exists(self.thumbnail_path)
    
    async def delete_thumbnail(self) -> bool:
        try:
            if os.path.exists(self.thumbnail_path):
                os.remove(self.thumbnail_path)
                return True
            return False
        except:
            return False

thumbnail_manager = LocalThumbnail()
    
