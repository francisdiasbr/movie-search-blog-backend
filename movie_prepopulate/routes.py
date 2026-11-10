from flask import Blueprint, request
from flask_restx import Namespace, Resource

from .controller import (
    get_prepopulate_stats,
    prepopulate_all_movies,
    prepopulate_movie_data,
    prepopulate_single_movie,
)

movie_prepopulate_bp = Blueprint("movie_prepopulate", __name__)
api = Namespace("prepopulate", description="Pré-população de dados de filmes")


@api.route("/stats")
class PrepopulateStats(Resource):
    @api.doc("get_prepopulate_stats")
    @api.response(200, "Sucesso")
    @api.response(500, "Erro ao buscar estatísticas")
    def get(self):
        """Retorna estatísticas de pré-população"""
        result = get_prepopulate_stats()
        return result, 500 if "error" in result else 200


@api.route("/all")
class PrepopulateAll(Resource):
    @api.doc("prepopulate_all")
    @api.response(200, "Sucesso")
    def post(self):
        """Pré-popula dados de todos os filmes"""
        data = request.get_json() or {}
        language = data.get("language", "pt")
        max_workers = data.get("max_workers", 3)
        result = prepopulate_all_movies(language, max_workers)
        status = 200 if result.get("status") == "completed" else 500
        return result, status


@api.route("/movie")
class PrepopulateMovie(Resource):
    @api.doc("prepopulate_movie")
    @api.response(200, "Sucesso")
    @api.response(400, "Dados obrigatórios")
    def post(self):
        """Pré-popula dados de um filme (usado ao inserir novo filme)"""
        data = request.get_json()
        if not data:
            return {"error": "Dados do filme são obrigatórios"}, 400
        language = data.get("language", "pt")
        result = prepopulate_movie_data(data, language)
        status = 200 if result.get("status") in ("success", "already_exists") else 500
        return result, status


@api.route("/<string:movie_id>")
class PrepopulateSingle(Resource):
    @api.doc("prepopulate_single")
    @api.response(200, "Sucesso")
    @api.response(404, "Filme não encontrado")
    def post(self, movie_id):
        """Pré-popula dados de um filme específico"""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        language = data.get("language", "pt")
        result = prepopulate_single_movie(movie_id, language)
        if result.get("status") == "not_found":
            return result, 404
        status = 200 if result.get("status") in ("success", "already_exists") else 500
        return result, status


movie_prepopulate_bp.api = api
