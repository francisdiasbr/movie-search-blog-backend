from flask import Blueprint, request
from flask_restx import Namespace, Resource
from images.controller import (
    get_public_image_url,
    get_all_image_urls
)
from config import BUCKET_NAME

images_bp = Blueprint("images", __name__)
api = Namespace(
    "images",
    description="Operações relacionadas à imagens de filmes"
)

@api.route("/<string:tconst>")
class Images(Resource):
    @api.doc("get_images")
    @api.response(200, "Sucesso")
    @api.response(404, "Imagens não encontradas")
    def get(self, tconst):
        """Recupera todas as URLs de imagens de um filme"""
        return get_all_image_urls(tconst) 


@api.route("/<string:tconst>/<string:filename>")
class ImageDetailOperations(Resource):
    @api.doc("get_public_image_url")
    @api.response(200, "URL gerada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro interno do servidor")
    def get(self, tconst, filename):
        """Gera uma URL pública direta para acessar a imagem no S3"""
        return get_public_image_url(BUCKET_NAME, tconst, filename)

