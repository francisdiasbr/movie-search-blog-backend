from flask import Blueprint, request
from flask_restx import Namespace, Resource
from favorites.models import favorite_movie_model, favorite_search_model
from favorites.controller import (
    get_favorited_movies
)

favorites_bp = Blueprint("favorites", __name__)
api = Namespace("favorites", description="Operações relacionadas aos filmes favoritos")

# Registra os modelos no namespace
api.model("FavoriteMovie", favorite_movie_model)
api.model("FavoriteSearch", favorite_search_model)

@api.route("/search")
class FavoriteMovieSearch(Resource):
    @api.doc("search_favorite_movies")
    @api.expect(api.model("FavoriteSearch", favorite_search_model))
    @api.response(200, "Sucesso")
    @api.response(400, "Dados de entrada inválidos")
    def post(self):
        """Pesquisa filmes favoritados"""
        request_data = request.get_json()
        if not isinstance(request_data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        return get_favorited_movies(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10),
            search_term=request_data.get("search_term", ""),
        ) 