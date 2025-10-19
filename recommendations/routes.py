from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from recommendations.controller import (
    get_random_recommendations,
    get_all_recommendations,
    delete_recommendation,
    clear_all_recommendations,
    add_recommendation,
    bulk_add_recommendations,
)

recommendations_bp = Blueprint("recommendations", __name__)
api = Namespace("recommendations", description="Operações relacionadas às recomendações de filmes")

# Modelo para o Swagger
recommendation_model = api.model(
    "Recommendation",
    {
        "tconst": fields.String(description="ID IMDB"),
        "title": fields.String(description="Título do filme"),
        "original_title": fields.String(description="Título original"),
        "year": fields.String(description="Ano de lançamento"),
        "director": fields.String(description="Diretor"),
        "genres": fields.String(description="Gêneros"),
        "imdb_rating": fields.String(description="Rating do IMDb"),
        "runtime": fields.String(description="Duração em minutos"),
        "position": fields.Integer(description="Posição na watchlist"),
        "url": fields.String(description="URL do IMDb"),
    },
)


@api.route("/")
class RecommendationsRoot(Resource):
    @api.doc("get_recommendations_info")
    @api.response(200, "Informações sobre as rotas de recomendações")
    def get(self):
        """Retorna informações sobre as rotas disponíveis"""
        return {
            "message": "Recommendations API",
            "available_routes": {
                "random": "/api/recommendations/random - Get random recommendations",
                "all": "/api/recommendations/all - Get all recommendations with pagination",
                "delete": "/api/recommendations/<tconst> - Delete a specific recommendation",
                "clear": "/api/recommendations/clear - Clear all recommendations"
            }
        }, 200


@api.route("/random")
class RandomRecommendations(Resource):
    @api.doc("get_random_recommendations")
    @api.response(200, "Sucesso")
    def get(self):
        """Retorna todas as recomendações"""
        return get_random_recommendations()


@api.route("/all")
class AllRecommendations(Resource):
    @api.doc("get_all_recommendations")
    @api.param("page", "Número da página", type=int, default=1)
    @api.param("page_size", "Tamanho da página", type=int, default=10)
    @api.param("search_term", "Termo de busca", type=str)
    @api.param("language", "Idioma (pt ou en)", type=str, default="pt")
    @api.response(200, "Sucesso")
    def get(self):
        """Retorna todas as recomendações com paginação"""
        page = request.args.get("page", default=1, type=int)
        page_size = request.args.get("page_size", default=10, type=int)
        search_term = request.args.get("search_term", default="", type=str)
        language = request.args.get("language", default="pt", type=str)
        
        # Valida o idioma
        if language not in ['pt', 'en']:
            language = 'pt'
            
        return get_all_recommendations(page, page_size, search_term, language)


@api.route("/<string:tconst>")
class RecommendationItem(Resource):
    @api.doc("delete_recommendation")
    @api.response(200, "Recomendação removida com sucesso")
    @api.response(404, "Recomendação não encontrada")
    def delete(self, tconst):
        """Remove uma recomendação"""
        return delete_recommendation(tconst)


@api.route("/clear")
class ClearRecommendations(Resource):
    @api.doc("clear_all_recommendations")
    @api.response(200, "Todas as recomendações foram removidas")
    def delete(self):
        """Remove todas as recomendações"""
        return clear_all_recommendations()


@api.route("/add")
class AddRecommendation(Resource):
    @api.doc("add_recommendation")
    @api.expect(recommendation_model)
    @api.param("language", "Idioma (pt ou en)", type=str, default="pt")
    @api.param("prepopulate", "Pré-popular dados automaticamente", type=bool, default=True)
    @api.response(201, "Filme adicionado com sucesso")
    @api.response(400, "Filme já existe ou dados inválidos")
    def post(self):
        """Adiciona uma nova recomendação"""
        data = request.get_json()
        language = request.args.get("language", default="pt", type=str)
        prepopulate = request.args.get("prepopulate", default=True, type=bool)
        
        if not data:
            return {"error": "Dados do filme são obrigatórios"}, 400
        
        return add_recommendation(data, language, prepopulate)


@api.route("/bulk-add")
class BulkAddRecommendations(Resource):
    @api.doc("bulk_add_recommendations")
    @api.param("language", "Idioma (pt ou en)", type=str, default="pt")
    @api.param("prepopulate", "Pré-popular dados automaticamente", type=bool, default=True)
    @api.response(201, "Filmes adicionados com sucesso")
    @api.response(400, "Todos os filmes já existem ou dados inválidos")
    def post(self):
        """Adiciona múltiplas recomendações"""
        data = request.get_json()
        language = request.args.get("language", default="pt", type=str)
        prepopulate = request.args.get("prepopulate", default=True, type=bool)
        
        if not data or not isinstance(data, list):
            return {"error": "Lista de filmes é obrigatória"}, 400
        
        return bulk_add_recommendations(data, language, prepopulate)


recommendations_bp.api = api

