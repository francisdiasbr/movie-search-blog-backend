import asyncio
import concurrent.futures
from datetime import datetime
from config import get_mongo_collection
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa os controllers existentes
from directors.controller import get_director_info
from music.controller import get_movie_soundtrack


def prepopulate_movie_data(movie_data, language="pt"):
    """Pré-popula dados de diretor e trilha sonora para um filme"""
    try:
        
        # Verifica se já tem dados salvos
        has_director = _check_existing_director(movie_data.get('director'))
        has_soundtrack = _check_existing_soundtrack(movie_data.get('title'), movie_data.get('year'))
        
        if has_director and has_soundtrack:
            return {"status": "already_exists", "message": "Dados já existem"}
        
        # Pré-popula dados em paralelo
        results = {}
        
        # Pré-popula diretor se não existe
        if not has_director and movie_data.get('director'):
            director_data, director_status = get_director_info(
                movie_data['director'], 
                movie_data.get('tconst'), 
                language
            )
            if director_status == 200:
                results['director'] = director_data
        
        # Pré-popula trilha sonora se não existe
        if not has_soundtrack:
            soundtrack_data, soundtrack_status = get_movie_soundtrack(
                movie_data['title'],
                movie_data.get('year'),
                movie_data.get('director'),
                language
            )
            if soundtrack_status == 200:
                results['soundtrack'] = soundtrack_data
        
        return {
            "status": "success", 
            "message": "Dados pré-populados com sucesso",
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Erro: {str(e)}"}


def prepopulate_all_movies(language="pt", max_workers=3):
    """Pré-popula dados para todos os filmes na coleção recommendations"""
    try:
        collection = get_mongo_collection("recommendations")
        
        # Busca todos os filmes
        movies = list(collection.find({}))
        total_movies = len(movies)
        
        
        # Processa em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for movie in movies:
                # Converte ObjectId para string
                movie["_id"] = str(movie["_id"])
                future = executor.submit(prepopulate_movie_data, movie, language)
                futures.append(future)
            
            # Coleta resultados
            results = []
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({"status": "error", "message": str(e)})
        
        # Estatísticas finais
        success_count = sum(1 for r in results if r.get('status') == 'success')
        already_exists_count = sum(1 for r in results if r.get('status') == 'already_exists')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        
        
        return {
            "status": "completed",
            "total_movies": total_movies,
            "success_count": success_count,
            "already_exists_count": already_exists_count,
            "error_count": error_count,
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Erro geral: {str(e)}"}


def _check_existing_director(director_name):
    """Verifica se diretor já existe no MongoDB"""
    if not director_name:
        return False
    
    try:
        directors_collection = get_mongo_collection("directors")
        return directors_collection.find_one({"name": director_name}) is not None
    except Exception:
        return False


def _check_existing_soundtrack(movie_title, movie_year):
    """Verifica se trilha sonora já existe no MongoDB"""
    try:
        soundtracks_collection = get_mongo_collection("movie_soundtracks")
        cache_key = f"{movie_title}_{movie_year}" if movie_year else movie_title
        return soundtracks_collection.find_one({"cache_key": cache_key}) is not None
    except Exception:
        return False


def get_prepopulate_stats():
    """Retorna estatísticas dos dados pré-populados"""
    try:
        # Estatísticas de diretores
        directors_collection = get_mongo_collection("directors")
        total_directors = directors_collection.count_documents({})
        
        # Estatísticas de trilhas sonoras
        soundtracks_collection = get_mongo_collection("movie_soundtracks")
        total_soundtracks = soundtracks_collection.count_documents({})
        
        # Estatísticas de filmes
        recommendations_collection = get_mongo_collection("recommendations")
        total_movies = recommendations_collection.count_documents({})
        
        # Cálculo de cobertura
        director_coverage = (total_directors / total_movies * 100) if total_movies > 0 else 0
        soundtrack_coverage = (total_soundtracks / total_movies * 100) if total_movies > 0 else 0
        
        return {
            "total_movies": total_movies,
            "total_directors": total_directors,
            "total_soundtracks": total_soundtracks,
            "director_coverage": round(director_coverage, 1),
            "soundtrack_coverage": round(soundtrack_coverage, 1),
            "overall_coverage": round((director_coverage + soundtrack_coverage) / 2, 1)
        }
        
    except Exception as e:
        return {"error": f"Erro ao buscar estatísticas: {str(e)}"}


def prepopulate_single_movie(movie_id, language="pt"):
    """Pré-popula dados para um filme específico"""
    try:
        collection = get_mongo_collection("recommendations")
        movie = collection.find_one({"tconst": movie_id})
        
        if not movie:
            return {"status": "error", "message": "Filme não encontrado"}
        
        movie["_id"] = str(movie["_id"])
        return prepopulate_movie_data(movie, language)
        
    except Exception as e:
        return {"status": "error", "message": f"Erro: {str(e)}"}
