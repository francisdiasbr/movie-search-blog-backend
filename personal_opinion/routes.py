from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from .controller import get_all_personal_opinions, get_personal_opinion, search_personal_opinions, update_personal_opinion


personal_opinion_bp = Blueprint("personal_opinion", __name__)
api = Namespace(
    "personal-opinion",
    description="Operações relacionadas a opiniões pessoais"
)

# Modelos para o Swagger
opinion_model = api.model(
    "PersonalOpinion",
    {
        "opinion": fields.String(description="Opinião pessoal", required=True),
        "enjoying_1": fields.String(description="Enjoying_1", required=True),
        "enjoying_2": fields.String(description="Enjoying_2", required=True)
    }
)

@api.route("/")
class AllPersonalOpinions(Resource):
    @api.doc("get_all_personal_opinions")
    @api.response(200, "Sucesso")
    @api.response(500, "Erro interno do servidor")
    def get(self):
        """Recupera todas as opiniões pessoais"""
        return get_all_personal_opinions()

    @api.doc("search_personal_opinions")
    @api.response(200, "Sucesso")
    @api.response(400, "Dados de entrada inválidos")
    @api.response(500, "Erro interno do servidor")
    def post(self):
        """Pesquisa opiniões pessoais com base em filtros e paginação"""
        data = request.get_json()
        if not isinstance(data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        
        filters = data.get("filters", {})
        page = data.get("page", 1)
        page_size = data.get("page_size", 10)
        
        return search_personal_opinions(filters, page, page_size)


@api.route("/<string:tconst>")
class PersonalOpinion(Resource):
    @api.doc("get_personal_opinion")
    @api.response(200, "Sucesso")
    @api.response(404, "Opinião não encontrada")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst):
        """Recupera a opinião pessoal para um filme específico"""
        return get_personal_opinion(tconst)

    @api.doc("update_personal_opinion")
    @api.expect(opinion_model)
    @api.response(200, "Opinião atualizada com sucesso")
    @api.response(400, "Dados de entrada inválidos")
    @api.response(404, "Opinião não encontrada")
    @api.response(500, "Erro interno do servidor")
    def put(self, tconst):
        """Atualiza uma opinião pessoal existente"""
        data = request.get_json()
        if not isinstance(data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
            
        return update_personal_opinion(tconst, data)

