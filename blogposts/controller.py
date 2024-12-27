from config import get_mongo_collection, BUCKET_NAME
import boto3
from botocore.exceptions import ClientError
import logging

def search_blog_post(request_data):
    """Pesquisa postagens de blog"""
    filters = request_data.get("filters", {})
    page = request_data.get("page", 1)
    page_size = request_data.get("page_size", 10)

    try:
        collection = get_mongo_collection("blogposts")
        
        # Construir filtros de busca
        search_filters = {}
        text_fields = ["tconst", "primaryTitle", "title", "introduction", 
                      "historical_context", "cultural_importance", 
                      "technical_analysis", "conclusion"]
        
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value

        # Contar total de documentos
        total_documents = collection.count_documents(search_filters)
        
        # Aplicar paginação
        skip = (page - 1) * page_size
        posts = list(
            collection.find(search_filters)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )

        # Processar documentos
        for post in posts:
            post["_id"] = str(post["_id"])

        return {
            "total_documents": total_documents,
            "entries": posts if posts else []
        }, 200 if total_documents > 0 else 404

    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": str(e)}, 500

def get_blog_post(tconst):
    """Recupera um post específico do blog"""
    try:
        collection = get_mongo_collection("blogposts")
        post = collection.find_one({"tconst": tconst})
        
        if post:
            post["_id"] = str(post["_id"])
            return post, 200
        return {"status": "erro", "mensagem": "Post não encontrado"}, 404

    except Exception as e:
        print(f"Erro: {e}")
        return {"status": "erro", "mensagem": str(e)}, 500

def get_all_image_urls(tconst):
    """Retorna todas as URLs de imagens associadas a um post"""
    try:
        s3_client = boto3.client('s3') 