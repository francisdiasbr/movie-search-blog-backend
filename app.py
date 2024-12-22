from flask import Flask, jsonify, request
import requests
from bson import ObjectId

from config import get_mongo_collection

app = Flask(__name__)

COLLECTION_NAME = "blogposts"

# Rota raiz simples
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Movie Search API is running",
        "docs": "/docs",
        "version": "1.0"
    })


def serialize_document(document):
    """Convert ObjectId to string in a MongoDB document."""
    if document is None:
        return document
    for key, value in document.items():
        if isinstance(value, ObjectId):
            document[key] = str(value)
    return document


@app.route('/api/generate-blogpost/<string:tconst>', methods=['GET'])
def get_blog_post(tconst):
    try:
        collection = get_mongo_collection(COLLECTION_NAME)
        
        existing_document = collection.find_one({"data.tconst": tconst})
        
        if existing_document:
            existing_document = serialize_document(existing_document)
            return jsonify(existing_document), 200
        
        # URL do endpoint existente
        url = f"http://127.0.0.1:5001/api/generate-blogpost/{tconst}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            
            data = serialize_document(data)
            return jsonify(data), 200
        else:
            # Retorna uma mensagem de erro se a requisição falhar
            return jsonify({"status": "erro", "mensagem": "Falha ao obter a postagem"}), response.status_code
    except requests.exceptions.RequestException as e:
        # Tratar erros e retornar uma resposta de erro
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route('/api/generate-blogpost/search', methods=['POST'])
def search_blog_post():
    """Pesquisa postagens de blog"""
    request_data = request.get_json()
    if not isinstance(request_data, dict):
        return jsonify({"status": 400, "message": "Dados de entrada inválidos"}), 400

    filters = request_data.get("filters", {})
    page = request_data.get("page", 1)
    page_size = request_data.get("page_size", 10)

    return jsonify(get_blogposts(filters, page, page_size))

def get_blogposts(filters={}, page=1, page_size=10):
    """Recupera todas as postagens de blog com paginação"""
    try:
        blogposts_collection = get_mongo_collection(COLLECTION_NAME)

        # Garante que os valores são inteiros
        page = int(page)
        page_size = int(page_size)
        
        # Converte filtros de texto para regex case-insensitive
        search_filters = {}
        text_fields = ["tconst", "primaryTitle", "title", "introduction", 
                      "historical_context", "cultural_importance", 
                      "technical_analysis", "conclusion"]
        
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value
        
        total_documents = blogposts_collection.count_documents(search_filters)
        skip = (page - 1) * page_size
        
        posts = list(
            blogposts_collection.find(search_filters, {"_id": 0})
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )

        return {
            "total_documents": total_documents,
            "entries": posts if posts else []
        }, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {
            "total_documents": 0,
            "entries": []
        }, 500 

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port, host='0.0.0.0')