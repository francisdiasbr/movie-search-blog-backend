from flask_restx import fields

# Modelos para o Swagger
favorite_movie_model = {
    "primaryTitle": fields.String(description="Título do filme"),
    "startYear": fields.Integer(description="Ano de lançamento"),
    "soundtrack": fields.String(description="Link da trilha sonora"),
    "wiki": fields.String(description="Link da Wikipedia"),
}

favorite_search_model = {
    "filters": fields.Raw(description="Filtros para a busca"),
    "page": fields.Integer(description="Número da página", default=1),
    "page_size": fields.Integer(description="Tamanho da página", default=10),
    "search_term": fields.String(description="Termo de busca", default=""),
} 