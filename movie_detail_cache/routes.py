from flask import Blueprint, request, jsonify
from .controller import (
    get_movie_detail_cache,
    invalidate_movie_cache,
    get_cache_stats,
    cleanup_expired_cache
)

movie_detail_cache_bp = Blueprint('movie_detail_cache', __name__)


@movie_detail_cache_bp.route('/movie-detail/<movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    """Endpoint para buscar cache completo de detalhes do filme"""
    try:
        language = request.args.get('language', 'pt')
        
        cache_data, status_code = get_movie_detail_cache(movie_id, language)
        
        if status_code == 200:
            return jsonify(cache_data), 200
        else:
            return jsonify(cache_data), status_code
            
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500


@movie_detail_cache_bp.route('/movie-detail/<movie_id>/invalidate', methods=['POST'])
def invalidate_cache(movie_id):
    """Endpoint para invalidar cache de um filme"""
    try:
        data = request.get_json() or {}
        language = data.get('language')
        
        result, status_code = invalidate_movie_cache(movie_id, language)
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500


@movie_detail_cache_bp.route('/movie-detail/stats', methods=['GET'])
def get_stats():
    """Endpoint para obter estatísticas do cache"""
    try:
        stats, status_code = get_cache_stats()
        return jsonify(stats), status_code
        
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500


@movie_detail_cache_bp.route('/movie-detail/cleanup', methods=['POST'])
def cleanup_cache():
    """Endpoint para limpar caches expirados"""
    try:
        result, status_code = cleanup_expired_cache()
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500
