from flask import Blueprint, request
from flask_restx import Namespace, Resource
from blogposts.models import blogpost_model, blogpost_search_model
from blogposts.controller import (
    search_blog_post,
    get_blog_post,
    get_all_image_urls
)

blogposts_bp = Blueprint("blogposts", __name__)
api = Namespace("blogposts", description="Operações relacionadas aos posts do blog")

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

@api.route("/images/<string:tconst>")
class BlogPostImages(Resource):
    @api.doc("get_blog_post_images")
    @api.response(200, "Sucesso")
    @api.response(404, "Imagens não encontradas")
    def get(self, tconst):
        """Recupera todas as URLs de imagens de um post"""
        return get_all_image_urls(tconst) 