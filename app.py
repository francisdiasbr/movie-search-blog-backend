from flask import Flask, jsonify, request
import requests
from bson import ObjectId

from config import get_mongo_collection

app = Flask(__name__)


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
        collection = get_mongo_collection("blogposts")
        
        existing_document = collection.find_one({"data.tconst": tconst})
        
        if existing_document:
            existing_document = serialize_document(existing_document)
            return jsonify(existing_document), 200
        
        # URL do endpoint existente
        url = f"http://127.0.0.1:5000/api/generate-blogpost/{tconst}"
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)