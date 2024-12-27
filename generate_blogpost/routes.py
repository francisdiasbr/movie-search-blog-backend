from flask import Blueprint, request
from flask_restx import Namespace, Resource

from generate_blogpost.models import blogpost_model, blogpost_search_model
from generate_blogpost.controller import (
    search_blog_post,
    get_blog_post
)

generate_blogpost_bp = Blueprint("generate_blogpost", __name__)
api = Namespace(
    "generate-blogpost",
    description="Operações relacionadas à geração de postagens de blog sobre filmes"
)
# Registrar os modelos
api.model("BlogPost", blogpost_model)
api.model("BlogPostSearch", blogpost_search_model)

@api.route("/search")
class BlogPostSearch(Resource):
    @api.doc("search_blog_posts")
    @api.expect(api.model("BlogPostSearch", blogpost_search_model))
    @api.response(200, "Sucesso")
    @api.response(404, "Nenhum resultado encontrado")
    def post(self):
        """Pesquisa posts do blog"""
        request_data = request.get_json()
        if not isinstance(request_data, dict):
            return {"status": 400, "message": "Dados de entrada inválidos"}, 400
        return search_blog_post(request_data)

@api.route("/<string:tconst>")
class BlogPost(Resource):
    @api.doc("get_blog_post")
    @api.response(200, "Sucesso")
    @api.response(404, "Post não encontrado")
    def get(self, tconst):
        """Recupera um post do blog específico"""
        return get_blog_post(tconst)
