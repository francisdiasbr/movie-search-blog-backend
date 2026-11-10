from flask import Blueprint, request
from flask_restx import Namespace, Resource

from .controller import (
    cleanup_expired_cache,
    get_cache_stats,
    get_movie_detail_cache,
    invalidate_movie_cache,
)

movie_detail_cache_bp = Blueprint("movie_detail_cache", __name__)
api = Namespace("movie-detail", description="Cache de detalhes de filmes")


@api.route("/stats")
class CacheStats(Resource):
    @api.doc("get_cache_stats")
    @api.response(200, "Sucesso")
    def get(self):
        """Retorna estatísticas do cache"""
        return get_cache_stats()


@api.route("/cleanup")
class CacheCleanup(Resource):
    @api.doc("cleanup_cache")
    @api.response(200, "Sucesso")
    def post(self):
        """Remove caches expirados"""
        return cleanup_expired_cache()


@api.route("/<string:movie_id>")
class MovieDetailCache(Resource):
    @api.doc("get_movie_detail")
    @api.param("language", "Idioma (pt ou en)", default="pt")
    @api.response(200, "Sucesso")
    @api.response(404, "Filme não encontrado")
    def get(self, movie_id):
        """Busca cache completo de detalhes do filme"""
        language = request.args.get("language", "pt")
        return get_movie_detail_cache(movie_id, language)


@api.route("/<string:movie_id>/invalidate")
class MovieDetailCacheInvalidate(Resource):
    @api.doc("invalidate_cache")
    @api.response(200, "Sucesso")
    def post(self, movie_id):
        """Invalida cache de um filme"""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        return invalidate_movie_cache(movie_id, data.get("language"))


movie_detail_cache_bp.api = api
