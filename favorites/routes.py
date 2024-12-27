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
    @api.response(404, "Nenhum resultado encontrado")
    @api.response(400, "Dados de entrada inválidos")
    def post(self):
        """Pesquisa filmes favoritados"""
        try:
            request_data = request.get_json()
            print(f"Dados recebidos na requisição: {request_data}")

            if not isinstance(request_data, dict):
                return {"status": 400, "message": "Dados de entrada inválidos"}, 400

            filters = request_data.get("filters", {})
            page = int(request_data.get("page", 1))
            page_size = int(request_data.get("page_size", 10))
            search_term = request_data.get("search_term", "")

            result, status_code = get_favorited_movies(
                filters=filters,
                page=page,
                page_size=page_size,
                search_term=search_term
            )

            return result, status_code

        except Exception as e:
            print(f"Erro ao processar requisição: {e}")
            return {
                "status": 500,
                "message": "Erro interno do servidor",
                "error": str(e)
            }, 500 