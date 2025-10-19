import json
from datetime import datetime, timedelta
from config import get_mongo_collection, OPENAI_API_KEY
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa os controllers existentes
from directors.controller import get_director_info
from music.controller import get_movie_soundtrack


def get_movie_detail_cache(movie_id, language="pt"):
    """Busca ou cria cache completo da página de detalhes do filme"""
    collection = get_mongo_collection("movie_detail_cache")
    
    try:
        # Verifica se existe cache válido (menos de 24 horas)
        cache_key = f"{movie_id}_{language}"
        cache_data = collection.find_one({"cache_key": cache_key})
        
        if cache_data:
            # Verifica se o cache ainda é válido (24 horas)
            cache_time = cache_data.get("created_at")
            if cache_time and isinstance(cache_time, datetime):
                if datetime.now() - cache_time < timedelta(hours=24):
                    # Cache válido, retorna os dados
                    cache_data["_id"] = str(cache_data["_id"])
                    cache_data["from_cache"] = True
                    cache_data["cache_age_hours"] = (datetime.now() - cache_time).total_seconds() / 3600
                    return cache_data, 200
                else:
                    # Cache expirado, remove
                    collection.delete_one({"cache_key": cache_key})
        
        # Se não tem cache válido, cria um novo
        return _create_movie_detail_cache(movie_id, language)
        
    except Exception as e:
        return {"error": "Erro ao buscar cache de detalhes do filme"}, 500


def _create_movie_detail_cache(movie_id, language="pt"):
    """Cria um novo cache com todos os dados da página de detalhes do filme"""
    collection = get_mongo_collection("movie_detail_cache")
    
    try:
        # Busca dados do filme
        movie_data = _get_movie_data(movie_id, language)
        
        if not movie_data:
            return {"error": "Filme não encontrado"}, 404
        
        # ✅ OTIMIZAÇÃO: Busca dados já salvos primeiro
        director_info = _get_existing_director_data(movie_data.get("director"), language)
        soundtrack_info = _get_existing_soundtrack_data(movie_data["title"], movie_data.get("year"), language)
        
        # Se não encontrou dados salvos, busca novos (mas de forma mais rápida)
        if not director_info and movie_data.get("director"):
            director_data, director_status = get_director_info(
                movie_data["director"], 
                movie_data.get("tconst"), 
                language
            )
            if director_status == 200:
                director_info = director_data
        
        if not soundtrack_info:
            soundtrack_data, soundtrack_status = get_movie_soundtrack(
                movie_data["title"],
                movie_data.get("year"),
                movie_data.get("director"),
                language
            )
            if soundtrack_status == 200:
                soundtrack_info = soundtrack_data
        
        # Monta o cache completo
        cache_data = {
            "cache_key": f"{movie_id}_{language}",
            "movie_id": movie_id,
            "language": language,
            "movie": movie_data,
            "director": director_info,
            "soundtrack": soundtrack_info,
            "created_at": datetime.now(),
            "from_cache": False
        }
        
        # Salva no banco
        result = collection.insert_one(cache_data)
        cache_data["_id"] = str(result.inserted_id)
        
        return cache_data, 200
        
    except Exception as e:
        return {"error": "Erro ao criar cache de detalhes do filme"}, 500


def _get_existing_director_data(director_name, language="pt"):
    """Busca dados do diretor já salvos no MongoDB"""
    if not director_name:
        return None
    
    try:
        directors_collection = get_mongo_collection("directors")
        director_data = directors_collection.find_one({"name": director_name})
        
        if director_data:
            director_data["_id"] = str(director_data["_id"])
            
            # Traduz biografia se necessário
            if language != "pt" and director_data.get("bio"):
                director_data["bio"] = _translate_director_bio(director_data["bio"], language)
            
            return director_data
        
        return None
        
    except Exception as e:
        return None


def _get_existing_soundtrack_data(movie_title, movie_year, language="pt"):
    """Busca dados da trilha sonora já salvos no MongoDB"""
    try:
        soundtracks_collection = get_mongo_collection("movie_soundtracks")
        cache_key = f"{movie_title}_{movie_year}" if movie_year else movie_title
        soundtrack_data = soundtracks_collection.find_one({"cache_key": cache_key})
        
        if soundtrack_data:
            soundtrack_data["_id"] = str(soundtrack_data["_id"])
            
            # Traduz descrição se necessário
            if language != "pt" and soundtrack_data.get("description"):
                soundtrack_data["description"] = _translate_soundtrack_description(
                    soundtrack_data["description"], 
                    language
                )
            
            return soundtrack_data
        
        return None
        
    except Exception as e:
        return None


def _translate_director_bio(bio, language):
    """Traduz biografia do diretor"""
    try:
        if not OPENAI_API_KEY or language == "pt":
            return bio
        
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"Translate the following film director biography to English. Maintain the same style and tone: {bio}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.3,
            timeout=3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return bio


def _translate_soundtrack_description(description, language):
    """Traduz descrição da trilha sonora"""
    try:
        if not OPENAI_API_KEY or language == "pt":
            return description
        
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"Translate the following soundtrack description to {language}: {description}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3,
            timeout=3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return description


def _get_movie_data(movie_id, language="pt"):
    """Busca dados básicos do filme"""
    try:
        # Importa o controller de recomendações para buscar dados do filme
        from recommendations.controller import get_all_recommendations
        
        # Busca o filme específico
        recommendations, status_code = get_all_recommendations(
            page=1,
            page_size=1,
            search_term=movie_id,
            language=language
        )
        
        if status_code == 200 and recommendations.get("entries") and len(recommendations["entries"]) > 0:
            return recommendations["entries"][0]
        
        return None
        
    except Exception as e:
        return None


def invalidate_movie_cache(movie_id, language=None):
    """Invalida cache de um filme específico"""
    collection = get_mongo_collection("movie_detail_cache")
    
    try:
        if language:
            # Invalida cache específico do idioma
            cache_key = f"{movie_id}_{language}"
            result = collection.delete_one({"cache_key": cache_key})
        else:
            # Invalida todos os caches do filme
            result = collection.delete_many({"movie_id": movie_id})
        
        return {"message": f"Cache invalidado para filme {movie_id}"}, 200
        
    except Exception as e:
        return {"error": "Erro ao invalidar cache"}, 500


def get_cache_stats():
    """Retorna estatísticas do cache"""
    collection = get_mongo_collection("movie_detail_cache")
    
    try:
        total_caches = collection.count_documents({})
        
        # Caches válidos (menos de 24 horas)
        valid_caches = collection.count_documents({
            "created_at": {"$gte": datetime.now() - timedelta(hours=24)}
        })
        
        # Caches expirados
        expired_caches = total_caches - valid_caches
        
        # Idiomas mais usados
        language_stats = list(collection.aggregate([
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        
        return {
            "total_caches": total_caches,
            "valid_caches": valid_caches,
            "expired_caches": expired_caches,
            "language_stats": language_stats
        }, 200
        
    except Exception as e:
        return {"error": "Erro ao buscar estatísticas do cache"}, 500


def cleanup_expired_cache():
    """Remove caches expirados (mais de 24 horas)"""
    collection = get_mongo_collection("movie_detail_cache")
    
    try:
        result = collection.delete_many({
            "created_at": {"$lt": datetime.now() - timedelta(hours=24)}
        })
        
        return {"message": f"{result.deleted_count} caches expirados removidos"}, 200
        
    except Exception as e:
        return {"error": "Erro ao limpar cache expirado"}, 500
