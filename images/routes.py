from flask import Blueprint
from flask_restx import Namespace, Resource

from config import BUCKET_NAME
from images.controller import get_all_image_urls, get_image_url

images_bp = Blueprint("images", __name__)
api = Namespace("images", description="Operações relacionadas à imagens de filmes")


@api.route("/<string:tconst>")
class Images(Resource):
    @api.doc("get_images")
    @api.response(200, "Sucesso (lista vazia quando o filme não tem imagens)")
    @api.response(500, "Erro ao listar imagens")
    def get(self, tconst):
        """Recupera todas as URLs de imagens de um filme"""
        return get_all_image_urls(BUCKET_NAME, tconst)


@api.route("/<string:tconst>/<string:filename>")
class ImageDetail(Resource):
    @api.doc("get_image_url")
    @api.response(200, "URL gerada com sucesso")
    @api.response(404, "Imagem não encontrada")
    @api.response(500, "Erro ao buscar imagem")
    def get(self, tconst, filename):
        """Gera uma URL pública direta para acessar a imagem no S3"""
        return get_image_url(BUCKET_NAME, tconst, filename)


images_bp.api = api
