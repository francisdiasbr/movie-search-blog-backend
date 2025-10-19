from flask import Blueprint, request, jsonify
from .controller import (
    prepopulate_movie_data,
    prepopulate_all_movies,
    prepopulate_single_movie,
    get_prepopulate_stats
)

movie_prepopulate_bp = Blueprint('movie_prepopulate', __name__)


@movie_prepopulate_bp.route('/prepopulate/all', methods=['POST'])
def prepopulate_all():
    """Endpoint para pré-popular dados de todos os filmes"""
    try:
        data = request.get_json() or {}
        language = data.get('language', 'pt')
        max_workers = data.get('max_workers', 3)
        
        result = prepopulate_all_movies(language, max_workers)
        
        if result.get('status') == 'completed':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500


@movie_prepopulate_bp.route('/prepopulate/<movie_id>', methods=['POST'])
def prepopulate_single(movie_id):
    """Endpoint para pré-popular dados de um filme específico"""
    try:
        data = request.get_json() or {}
        language = data.get('language', 'pt')
        
        result = prepopulate_single_movie(movie_id, language)
        
        if result.get('status') in ['success', 'already_exists']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500


@movie_prepopulate_bp.route('/prepopulate/stats', methods=['GET'])
def get_stats():
    """Endpoint para obter estatísticas de pré-população"""
    try:
        stats = get_prepopulate_stats()
        
        if 'error' in stats:
            return jsonify(stats), 500
        else:
            return jsonify(stats), 200
            
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500


@movie_prepopulate_bp.route('/prepopulate/movie', methods=['POST'])
def prepopulate_movie():
    """Endpoint para pré-popular dados de um filme (usado quando filme é inserido)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados do filme são obrigatórios"}), 400
        
        language = data.get('language', 'pt')
        
        result = prepopulate_movie_data(data, language)
        
        if result.get('status') in ['success', 'already_exists']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500
