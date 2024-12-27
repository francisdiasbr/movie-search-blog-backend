from flask import Blueprint, request
from flask_restx import Namespace, Resource
from personal_opinion.controller import (
    get_all_image_urls
)

personal_opinion_bp = Blueprint("personal_opinion", __name__)
api = Namespace(
    "personal-opinion",
    description="Operações relacionadas à opinião pessoal sobre filmes"
)

@api.route("/get-all-image-urls/<string:tconst>")
class PersonalOpinionImages(Resource):
    @api.doc("get_personal_opinion_images")
    @api.response(200, "Sucesso")
    @api.response(404, "Imagens não encontradas")
    def get(self, tconst):
        """Recupera todas as URLs de imagens de um post"""
        return get_all_image_urls(tconst) 