import os

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

_mongo_client = None


def get_mongo_client():
    global _mongo_client
    if _mongo_client:
        return _mongo_client
    try:
        client = MongoClient(MONGODB_CONNECTION_STRING)
        client.server_info()
        _mongo_client = client
        print("Conexão com MongoDB estabelecida com sucesso (reutilizável)")
        return _mongo_client
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        return None


def get_mongo_collection(name):
    try:
        client = get_mongo_client()
        if client:
            return client[MONGODB_DATABASE][name]
        print(f"Não foi possível obter cliente MongoDB")
        return None
    except Exception as e:
        print(f"Erro ao obter coleção {name}: {e}")
        return None
