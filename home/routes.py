from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from .controller import get_home_cards

home_bp = Blueprint("home", __name__)
api = Namespace("home", description="Dados para a página inicial do blog")

cards_search_input = api.model(
    "HomeCardsInput",
    {
        "filters": fields.Raw(description="Filtros de busca", default={}),
        "page": fields.Integer(default=1),
        "page_size": fields.Integer(default=10),
    },
)

card_output = api.model(
    "HomeCard",
    {
        "_id": fields.String(),
        "tconst": fields.String(),
        "primaryTitle": fields.String(),
        "created_at": fields.String(),
        "imageUrl": fields.String(),
    },
)

cards_output = api.model(
    "HomeCardsOutput",
    {
        "entries": fields.List(fields.Nested(card_output)),
        "total_documents": fields.Integer(),
    },
)


@api.route("/cards")
class HomeCards(Resource):
    @api.doc("get_home_cards")
    @api.expect(cards_search_input)
    @api.response(200, "Sucesso", cards_output)
    def post(self):
        """Retorna cards otimizados para a página inicial"""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        return get_home_cards(
            filters=data.get("filters", {}),
            page=data.get("page", 1),
            page_size=data.get("page_size", 10),
        )


home_bp.api = api
