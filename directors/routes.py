from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from directors.controller import (
    get_director_info,
    get_all_directors,
    delete_director,
)

directors_bp = Blueprint("directors", __name__)
api = Namespace("directors", description="Operações relacionadas aos diretores")

# Modelo para o Swagger
director_model = api.model(
    "Director",
    {
        "name": fields.String(description="Nome do diretor"),
        "bio": fields.String(description="Biografia do diretor"),
        "photo": fields.String(description="URL da foto do diretor"),
    },
)


@api.route("/")
class DirectorsRoot(Resource):
    @api.doc("get_directors_info")
    @api.response(200, "Informações sobre as rotas de diretores")
    def get(self):
        """Retorna informações sobre as rotas disponíveis"""
        return {
            "message": "Directors API",
            "available_routes": {
                "director": "/api/directors/<director_name> - Get director information",
                "all": "/api/directors/all - Get all directors",
                "delete": "/api/directors/<director_name> - Delete a specific director"
            }
        }, 200


@api.route("/<string:director_name>")
class DirectorItem(Resource):
    @api.doc("get_director_info")
    @api.response(200, "Informações do diretor")
    @api.response(500, "Erro ao buscar informações do diretor")
    def get(self, director_name):
        """Retorna informações de um diretor específico"""
        return get_director_info(director_name)

    @api.doc("delete_director")
    @api.response(200, "Diretor removido com sucesso")
    @api.response(404, "Diretor não encontrado")
    def delete(self, director_name):
        """Remove um diretor"""
        return delete_director(director_name)


@api.route("/all")
class AllDirectors(Resource):
    @api.doc("get_all_directors")
    @api.response(200, "Lista de todos os diretores")
    def get(self):
        """Retorna todos os diretores salvos no banco"""
        return get_all_directors()


directors_bp.api = api
