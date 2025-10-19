from flask import Blueprint, request
from flask_restx import Namespace, Resource, fields

from music.controller import (
    get_movie_soundtrack,
    get_all_soundtracks,
    delete_soundtrack,
)

music_bp = Blueprint("music", __name__)
api = Namespace("music", description="Operações relacionadas às trilhas sonoras dos filmes")

# Modelo para o Swagger
track_model = api.model(
    "Track",
    {
        "title": fields.String(description="Nome da música"),
        "artist": fields.String(description="Nome do artista"),
        "spotify_id": fields.String(description="ID da música no Spotify"),
        "preview_url": fields.String(description="URL de preview da música"),
        "external_urls": fields.Raw(description="URLs externas (Spotify, etc.)"),
        "album": fields.Raw(description="Informações do álbum"),
        "duration_ms": fields.Integer(description="Duração em milissegundos"),
        "description": fields.String(description="Descrição da música no filme"),
    },
)

soundtrack_model = api.model(
    "Soundtrack",
    {
        "movie_title": fields.String(description="Título do filme"),
        "movie_year": fields.Integer(description="Ano do filme"),
        "movie_director": fields.String(description="Diretor do filme"),
        "tracks": fields.List(fields.Nested(track_model), description="Lista de músicas"),
        "description": fields.String(description="Descrição da trilha sonora"),
        "source": fields.String(description="Fonte dos dados"),
    },
)


@api.route("/")
class MusicRoot(Resource):
    @api.doc("get_music_info")
    @api.response(200, "Informações sobre as rotas de música")
    def get(self):
        """Retorna informações sobre as rotas disponíveis"""
        return {
            "message": "Music API",
            "available_routes": {
                "soundtrack": "/api/music/soundtrack - Get movie soundtrack",
                "all": "/api/music/all - Get all soundtracks",
                "delete": "/api/music/soundtrack - Delete a specific soundtrack"
            }
        }, 200


@api.route("/soundtrack")
class SoundtrackResource(Resource):
    @api.doc("get_movie_soundtrack")
    @api.param("title", "Título do filme", required=True)
    @api.param("year", "Ano do filme", type="int")
    @api.param("director", "Diretor do filme")
    @api.response(200, "Trilha sonora do filme", soundtrack_model)
    @api.response(404, "Trilha sonora não encontrada")
    @api.response(500, "Erro ao buscar trilha sonora")
    def get(self):
        """Retorna a trilha sonora de um filme específico"""
        movie_title = request.args.get('title')
        movie_year = request.args.get('year', type=int)
        movie_director = request.args.get('director')
        
        if not movie_title:
            return {"error": "Título do filme é obrigatório"}, 400
        
        return get_movie_soundtrack(movie_title, movie_year, movie_director)

    @api.doc("delete_soundtrack")
    @api.param("title", "Título do filme", required=True)
    @api.param("year", "Ano do filme", type="int")
    @api.response(200, "Trilha sonora removida com sucesso")
    @api.response(404, "Trilha sonora não encontrada")
    def delete(self):
        """Remove uma trilha sonora"""
        movie_title = request.args.get('title')
        movie_year = request.args.get('year', type=int)
        
        if not movie_title:
            return {"error": "Título do filme é obrigatório"}, 400
        
        return delete_soundtrack(movie_title, movie_year)


@api.route("/all")
class AllSoundtracks(Resource):
    @api.doc("get_all_soundtracks")
    @api.response(200, "Lista de todas as trilhas sonoras")
    def get(self):
        """Retorna todas as trilhas sonoras salvas no banco"""
        return get_all_soundtracks()


music_bp.api = api
