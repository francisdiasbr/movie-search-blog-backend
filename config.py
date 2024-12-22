import os

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


# String de conexão com o MongoDB
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

# Conexão com o MongoDB
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client[MONGODB_DATABASE]


# Função para obter uma coleção do MongoDB
def get_mongo_collection(name):
    collection = db[name]
    return collection