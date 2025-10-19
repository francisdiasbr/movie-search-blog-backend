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


def add_recommendation(movie_data, language="pt", prepopulate=True):
    """Adiciona uma nova recomendação e pré-popula dados se solicitado"""
    collection = get_mongo_collection("recommendations")
    
    try:
        # Verifica se o filme já existe
        existing = collection.find_one({"tconst": movie_data.get("tconst")})
        if existing:
            return {"error": "Filme já existe na base de dados"}, 400
        
        # Adiciona posição se não especificada
        if "position" not in movie_data:
            max_position = collection.find_one(sort=[("position", -1)])
            movie_data["position"] = (max_position["position"] + 1) if max_position else 1
        
        # Insere o filme
        result = collection.insert_one(movie_data)
        movie_data["_id"] = str(result.inserted_id)
        
        # Pré-popula dados se solicitado
        if prepopulate:
            try:
                from movie_prepopulate.controller import prepopulate_movie_data
                prepopulate_result = prepopulate_movie_data(movie_data, language)
                
                return {
                    "data": "Filme adicionado e dados pré-populados com sucesso",
                    "movie": movie_data,
                    "prepopulate": prepopulate_result
                }, 201
            except Exception as prepopulate_error:
                # Se pré-população falhar, ainda retorna sucesso para inserção
                return {
                    "data": "Filme adicionado com sucesso (pré-população falhou)",
                    "movie": movie_data,
                    "prepopulate_error": str(prepopulate_error)
                }, 201
        else:
            return {
                "data": "Filme adicionado com sucesso",
                "movie": movie_data
            }, 201
            
    except Exception as e:
        return {"error": f"Erro ao adicionar filme: {str(e)}"}, 500


def bulk_add_recommendations(movies_data, language="pt", prepopulate=True):
    """Adiciona múltiplas recomendações e pré-popula dados"""
    collection = get_mongo_collection("recommendations")
    
    try:
        # Verifica filmes duplicados
        tconsts = [movie.get("tconst") for movie in movies_data if movie.get("tconst")]
        existing_tconsts = set(doc["tconst"] for doc in collection.find({"tconst": {"$in": tconsts}}, {"tconst": 1}))
        
        # Filtra filmes que não existem
        new_movies = [movie for movie in movies_data if movie.get("tconst") not in existing_tconsts]
        
        if not new_movies:
            return {"error": "Todos os filmes já existem na base de dados"}, 400
        
        # Adiciona posições
        max_position = collection.find_one(sort=[("position", -1)])
        current_position = (max_position["position"] + 1) if max_position else 1
        
        for movie in new_movies:
            if "position" not in movie:
                movie["position"] = current_position
                current_position += 1
        
        # Insere filmes em lote
        result = collection.insert_many(new_movies)
        
        # Converte ObjectIds para strings
        for i, movie in enumerate(new_movies):
            movie["_id"] = str(result.inserted_ids[i])
        
        # Pré-popula dados se solicitado
        prepopulate_results = []
        if prepopulate:
            try:
                from movie_prepopulate.controller import prepopulate_movie_data
                
                for movie in new_movies:
                    prepopulate_result = prepopulate_movie_data(movie, language)
                    prepopulate_results.append({
                        "tconst": movie.get("tconst"),
                        "title": movie.get("title"),
                        "result": prepopulate_result
                    })
            except Exception as prepopulate_error:
                prepopulate_results = [{"error": str(prepopulate_error)}]
        
        return {
            "data": f"{len(new_movies)} filmes adicionados com sucesso",
            "movies": new_movies,
            "prepopulate_results": prepopulate_results,
            "skipped": len(movies_data) - len(new_movies)
        }, 201
        
    except Exception as e:
        return {"error": f"Erro ao adicionar filmes: {str(e)}"}, 500

