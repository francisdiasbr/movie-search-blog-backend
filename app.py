from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bson import ObjectId
import os
from flask_restx import Api, Resource
import boto3
from botocore.exceptions import ClientError
import logging

from config import get_mongo_collection, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BUCKET_NAME
from favorites.routes import favorites_bp, api as favorites_api

app = Flask(__name__)
CORS(app)

# Criar a API antes de registrar os namespaces
api = Api(app,
    title='Movie Search API',
    version='1.0',
    description='API para busca e gerenciamento de filmes'
)

# Registrar o namespace dos favoritos primeiro
api.add_namespace(favorites_api, path='/api/favorites')

# Depois registrar o blueprint
app.register_blueprint(favorites_bp, url_prefix='/api/favorites')

COLLECTION_NAME = "blogposts"

# Configurar o nível de log do PyMongo
logging.getLogger('pymongo').setLevel(logging.WARNING)

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


@app.route('/api/generate-blogpost/search', methods=['POST'])
def search_blog_post():
    """Pesquisa postagens de blog"""
    request_data = request.get_json()
    if not isinstance(request_data, dict):
        return jsonify({"status": 400, "message": "Dados de entrada inválidos"}), 400

    filters = request_data.get("filters", {})
    page = request_data.get("page", 1)
    page_size = request_data.get("page_size", 10)

    result = get_blogposts(filters, page, page_size)
    status_code = 200 if result["total_documents"] > 0 else 404
    return jsonify(result), status_code

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
        }
    except Exception as e:
        print(f"Erro: {e}")
        return {
            "total_documents": 0,
            "entries": []
        }



@app.route('/api/generate-blogpost/<string:tconst>', methods=['GET'])
def get_blog_post(tconst):
    try:
        print(f"Recebendo solicitação para tconst: {tconst}")
        
        collection = get_mongo_collection(COLLECTION_NAME)
        print("Conexão com a coleção MongoDB estabelecida.")
        
        existing_document = collection.find_one({"tconst": tconst})
        print(f"Documento encontrado: {existing_document}")
        
        if existing_document:
            existing_document = serialize_document(existing_document)
            print(f"Documento serializado: {existing_document}")
            return jsonify(existing_document), 200
        else:
            print("Documento não encontrado.")
            return jsonify({"status": "erro", "mensagem": "Documento não encontrado"}), 404
    except Exception as e:
        print(f"Erro ao processar a solicitação: {e}")
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@api.route("/api/personal-opinion/get-all-image-urls/<string:tconst>")
class GetAllImageUrls(Resource):
    @api.doc("get_all_image_urls")
    @api.response(200, "URLs geradas com sucesso")
    @api.response(404, "Imagens não encontradas")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Gera todas as URLs públicas diretas para imagens associadas a um tconst"""
        return get_all_image_urls(BUCKET_NAME, tconst)

def get_all_image_urls(bucket_name, tconst):
    """Retorna todas as URLs públicas diretas e nomes de arquivos para imagens associadas a um tconst"""

    print(f"Iniciando a obtenção de URLs de imagens para tconst: {tconst} no bucket: {bucket_name}")

    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name='us-east-2'
    )
    
    try:
        # Lista todos os objetos no bucket que começam com o prefixo tconst
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{tconst}/")
        print(f"Resposta do S3: {response}")

        images = []
        for obj in response.get('Contents', []):
            object_name = obj['Key']
            filename = object_name.split('/')[-1]
            
            url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_name}"
            images.append({
                "url": url,
                "filename": filename,
                "last_modified": obj['LastModified']
            })
        
        images.sort(key=lambda x: x['last_modified'])
        
        for image in images:
            del image['last_modified']
        
        print(f"Imagens encontradas: {images}")
        return {"images": images}, 200
    except ClientError as e:
        print(f"Erro ao listar objetos no S3: {e}")
        return {"status": 500, "message": "Erro ao listar imagens"}, 500
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return {"status": 500, "message": "Erro inesperado"}, 500

if __name__ == '__main__':
    # Configurar o nível de log para DEBUG
    logging.basicConfig(level=logging.DEBUG)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port, host='0.0.0.0')