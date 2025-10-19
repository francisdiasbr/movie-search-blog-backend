from config import get_mongo_collection
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_random_recommendations():
    """Retorna todas as recomendações da watchlist"""
    collection = get_mongo_collection("recommendations")
    
    try:
        # Conta total de documentos
        total_count = collection.count_documents({})
        
        if total_count == 0:
            return {"data": [], "total": 0}, 200
        
        # Retorna todos os registros ordenados por posição
        recommendations = list(collection.find({}).sort("position", 1))
        
        # Converte ObjectId para string
        for rec in recommendations:
            rec["_id"] = str(rec["_id"])
        
        return {"data": recommendations, "total": total_count}, 200
    except Exception as e:
        return {"status": 500, "message": "Erro ao buscar recomendações"}, 500


def get_all_recommendations(page=1, page_size=10, search_term="", language="pt"):
    """Retorna todas as recomendações com paginação e busca"""
    collection = get_mongo_collection("recommendations")
    
    filters = {}
    
    # Filtra por termo de busca
    if search_term:
        filters["$or"] = [
            {"tconst": search_term},
            {"title": {"$regex": search_term, "$options": "i"}},
            {"director": {"$regex": search_term, "$options": "i"}},
        ]
    
    try:
        total_documents = collection.count_documents(filters)
        skip = (page - 1) * page_size
        
        items = list(
            collection.find(filters)
            .sort("position", 1)  # Ordena pela posição da watchlist
            .skip(skip)
            .limit(page_size)
        )
        
        for item in items:
            item["_id"] = str(item["_id"])
        
        return {
            "total_documents": total_documents,
            "entries": items,
        }, 200
    except Exception as e:
        return {"status": 500, "message": "Erro ao buscar recomendações"}, 500


def delete_recommendation(tconst):
    """Remove uma recomendação"""
    collection = get_mongo_collection("recommendations")
    
    try:
        result = collection.delete_one({"tconst": tconst})
        
        if result.deleted_count == 1:
            return {"data": f"Recommendation {tconst} deleted"}, 200
        else:
            return {"data": f"Recommendation {tconst} not found"}, 404
    except Exception as e:
        return {"data": "Failed to delete recommendation"}, 500


def clear_all_recommendations():
    """Remove todas as recomendações (útil para re-importar)"""
    collection = get_mongo_collection("recommendations")
    
    try:
        result = collection.delete_many({})
        return {"data": f"{result.deleted_count} recommendations deleted"}, 200
    except Exception as e:
        return {"data": "Failed to clear recommendations"}, 500

