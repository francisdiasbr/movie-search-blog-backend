from flask_restx import fields

blogpost_search_model = {
    "filters": fields.Raw(description="Filtros para a busca"),
    "page": fields.Integer(description="Número da página", default=1),
    "page_size": fields.Integer(description="Tamanho da página", default=10),
}

blogpost_model = {
    "tconst": fields.String(required=True, description="ID do filme"),
    "primaryTitle": fields.String(required=True, description="Título do filme"),
    "content": fields.Raw(description="Conteúdo do blog post em diferentes idiomas"),
    "created_at": fields.DateTime(description="Data de criação"),
    "images": fields.List(fields.String, description="URLs das imagens"),
    "poster_url": fields.String(description="URL do poster"),
    "references": fields.List(fields.String, description="Referências"),
    "soundtrack": fields.String(description="URL da trilha sonora no Spotify"),
} 