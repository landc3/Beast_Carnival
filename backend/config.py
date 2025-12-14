import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-7e1aeb711dec4355b53ecd8ff0116057")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 1998))

config = Config()

