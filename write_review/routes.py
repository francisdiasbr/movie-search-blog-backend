from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from .controller import get_write_review, search_write_reviews


write_review_bp = Blueprint("write_review", __name__)

api = Namespace(
    "write-review", description="Operações relacionadas a resenhas escritas"
)

review_output = api.model(
    "ReviewOutput",
    {
        "data": fields.Nested(
            api.model(
                "ReviewDocument",
                {
                    "tconst": fields.String(description="ID do filme"),
                    "primaryTitle": fields.String(description="Título do filme"),
                    "content": fields.Nested(
                        api.model(
                            "ReviewContentOutput",
                            {
                                "en": fields.Nested(
                                    api.model(
                                        "ReviewContent", {"text": fields.String()}
                                    )
                                ),
                                "pt": fields.Nested(
                                    api.model(
                                        "ReviewContentPt", {"text": fields.String()}
                                    )
                                ),
                            },
                        )
                    ),
                    "created_at": fields.String(description="Data de criação"),
                    "isAiGenerated": fields.Boolean(),
                    "references": fields.List(fields.String),
                    "images": fields.List(fields.String),
                },
            )
        )
    },
)

search_input = api.model(
    "ReviewSearchInput",
    {
        "filters": fields.Raw(description="Filtros de busca", default={}),
        "page": fields.Integer(default=1),
        "page_size": fields.Integer(default=10),
    },
)


@api.route("/<string:tconst>")
class MovieReview(Resource):
    @api.doc("get_review")
    @api.response(200, "Success", review_output)
    @api.response(404, "Review not found")
    def get(self, tconst):
        """Obtém a resenha de um filme específico"""
        return get_write_review(tconst)


@api.route("/search")
class ReviewSearch(Resource):
    @api.doc("search_reviews")
    @api.expect(search_input)
    @api.response(200, "Success")
    def post(self):
        """Busca resenhas com filtros"""
        request_data = request.get_json() or {}
        return search_write_reviews(
            filters=request_data.get("filters", {}),
            page=request_data.get("page", 1),
            page_size=request_data.get("page_size", 10),
        )


write_review_bp.api = api
