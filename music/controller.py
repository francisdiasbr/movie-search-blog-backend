import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from openai import OpenAI
from config import get_mongo_collection, OPENAI_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _translate_soundtrack_description(description, target_language):
    """Traduz a descrição da trilha sonora"""
    try:
        if not OPENAI_API_KEY or target_language == "pt":
            return description
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"Translate the following soundtrack description to {target_language}: {description}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate movie soundtrack descriptions accurately."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Reduzido para resposta mais rápida
            temperature=0.3,
            timeout=3  # Timeout de 3 segundos
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return description


def get_movie_soundtrack(movie_title, movie_year=None, movie_director=None, language="pt"):
    """Busca a trilha sonora de um filme usando GPT e Spotify"""
    collection = get_mongo_collection("movie_soundtracks")
    
    try:
        # Primeiro tenta buscar no banco de dados
        cache_key = f"{movie_title}_{movie_year}" if movie_year else movie_title
        soundtrack_data = collection.find_one({"cache_key": cache_key})
        
        if soundtrack_data:
            # Converte ObjectId para string
            soundtrack_data["_id"] = str(soundtrack_data["_id"])
            
            # Traduz a descrição se necessário
            if language != "pt" and soundtrack_data.get("description"):
                # Tradução simples sem cache
                soundtrack_data["description"] = _translate_soundtrack_description(
                    soundtrack_data["description"], 
                    language
                )
            
            return soundtrack_data, 200
        
        # Se não encontrou no banco, busca usando GPT + Spotify
        soundtrack_info = _get_soundtrack_with_gpt_and_spotify(movie_title, movie_year, movie_director, language)
        
        if soundtrack_info:
            # Adiciona cache_key para futuras consultas
            soundtrack_info["cache_key"] = cache_key
            
            # Salva no banco para futuras consultas
            result = collection.insert_one(soundtrack_info)
            soundtrack_info["_id"] = str(result.inserted_id)
            return soundtrack_info, 200
        
        error_message = "Não foi possível encontrar a trilha sonora do filme" if language == "pt" else "Could not find movie soundtrack"
        return {"error": error_message}, 404
        
    except Exception as e:
        error_message = "Erro ao buscar trilha sonora" if language == "pt" else "Error searching soundtrack"
        return {"error": error_message}, 500


def _get_soundtrack_with_gpt_and_spotify(movie_title, movie_year=None, movie_director=None, language="pt"):
    """Usa GPT para identificar as principais músicas do filme e busca no Spotify"""
    try:
        # 1. Usa GPT para identificar as principais músicas do filme
        track_info = _get_track_info_with_gpt(movie_title, movie_year, movie_director, language)
        
        if not track_info or not track_info.get("tracks"):
            return None
        
        # 2. Busca as músicas no Spotify
        spotify_tracks = _search_tracks_on_spotify(track_info["tracks"])
        
        return {
            "movie_title": movie_title,
            "movie_year": movie_year,
            "movie_director": movie_director,
            "tracks": spotify_tracks,
            "description": track_info.get("description", ""),
            "source": "gpt_spotify"
        }
        
    except Exception as e:
        return None


def _get_track_info_with_gpt(movie_title, movie_year=None, movie_director=None, language="pt"):
    """Usa GPT para identificar as principais músicas do filme"""
    try:
        if not OPENAI_API_KEY:
            return None
        
        # Configura a API da OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Monta o prompt
        movie_info = f"Filme: {movie_title}"
        if movie_year:
            movie_info += f" ({movie_year})"
        if movie_director:
            movie_info += f" - Diretor: {movie_director}"
        
        if language == "en":
            prompt = f"""
            Identify the main songs/soundtracks from the movie "{movie_title}".
            
            {movie_info}
            
            Please provide:
            1. A list of the 5-8 most important/iconic songs from the movie
            2. For each song, include: song name, artist/composer
            3. A brief description of the importance of the soundtrack in the movie
            
            Response format (JSON):
            {{
                "tracks": [
                    {{
                        "title": "Song name",
                        "artist": "Artist/composer name",
                        "description": "Brief description of the song in the movie"
                    }}
                ],
                "description": "General soundtrack description"
            }}
            
            If you don't know specific information about the movie, be honest but try 
            to identify known songs associated with the movie.
            """
        else:
            prompt = f"""
            Identifique as principais músicas/trilhas sonoras do filme "{movie_title}".
            
            {movie_info}
            
            Por favor, forneça:
            1. Uma lista das 5-8 músicas mais importantes/icônicas do filme
            2. Para cada música, inclua: nome da música, artista/compositor
            3. Uma breve descrição da importância da trilha sonora no filme
            
            Formato de resposta (JSON):
            {{
                "tracks": [
                    {{
                        "title": "Nome da música",
                        "artist": "Nome do artista/compositor",
                        "description": "Breve descrição da música no filme"
                    }}
                ],
                "description": "Descrição geral da trilha sonora"
            }}
            
            Se não souber informações específicas sobre o filme, seja honesto mas tente 
            identificar músicas conhecidas associadas ao filme.
            """
        
        system_message = "You are a cinema and music expert. Identifies iconic movie soundtracks." if language == "en" else "Você é um especialista em cinema e música. Identifica trilhas sonoras icônicas de filmes."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # Reduzido para resposta mais rápida
            temperature=0.7,
            timeout=5  # Timeout de 5 segundos
        )
        
        # Tenta extrair JSON da resposta
        import json
        import re
        
        content = response.choices[0].message.content.strip()
        
        # Procura por JSON na resposta
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Se não conseguiu extrair JSON, tenta uma abordagem mais simples
        return _parse_gpt_response_manually(content)
        
    except Exception as e:
        return None


def _parse_gpt_response_manually(content):
    """Parse manual da resposta do GPT quando não consegue extrair JSON"""
    try:
        lines = content.split('\n')
        tracks = []
        description = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or line.startswith('5.'):
                # Tenta extrair título e artista
                parts = line.split(' - ')
                if len(parts) >= 2:
                    title = parts[0].split('.', 1)[1].strip() if '.' in parts[0] else parts[0].strip()
                    artist = parts[1].strip()
                    tracks.append({
                        "title": title,
                        "artist": artist,
                        "description": ""
                    })
            elif line and not line.startswith('{') and not line.startswith('}'):
                if not description:
                    description = line
        
        return {
            "tracks": tracks[:8],  # Limita a 8 músicas
            "description": description
        }
        
    except Exception as e:
        return None


def _search_tracks_on_spotify(tracks_info):
    """Busca as músicas no Spotify"""
    try:
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            return []
        
        # Configura autenticação do Spotify
        client_credentials_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        
        spotify_tracks = []
        
        for track_info in tracks_info:
            try:
                # Busca a música no Spotify
                query = f"track:{track_info['title']} artist:{track_info['artist']}"
                results = sp.search(q=query, type='track', limit=1)
                
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    
                    spotify_tracks.append({
                        "title": track['name'],
                        "artist": track['artists'][0]['name'],
                        "spotify_id": track['id'],
                        "preview_url": track.get('preview_url'),
                        "external_urls": track.get('external_urls', {}),
                        "album": {
                            "name": track['album']['name'],
                            "images": track['album']['images']
                        },
                        "duration_ms": track['duration_ms'],
                        "description": track_info.get('description', '')
                    })
                else:
                    # Se não encontrou, adiciona sem dados do Spotify
                    spotify_tracks.append({
                        "title": track_info['title'],
                        "artist": track_info['artist'],
                        "spotify_id": None,
                        "preview_url": None,
                        "external_urls": {},
                        "album": None,
                        "duration_ms": None,
                        "description": track_info.get('description', '')
                    })
                    
            except Exception as e:
                # Adiciona sem dados do Spotify
                spotify_tracks.append({
                    "title": track_info['title'],
                    "artist": track_info['artist'],
                    "spotify_id": None,
                    "preview_url": None,
                    "external_urls": {},
                    "album": None,
                    "duration_ms": None,
                    "description": track_info.get('description', '')
                })
        
        return spotify_tracks
        
    except Exception as e:
        return []


def get_all_soundtracks():
    """Retorna todas as trilhas sonoras salvas no banco"""
    collection = get_mongo_collection("movie_soundtracks")
    
    try:
        soundtracks = list(collection.find({}, {"_id": 0}))
        return {"soundtracks": soundtracks}, 200
    except Exception as e:
        return {"error": "Erro ao buscar trilhas sonoras"}, 500


def delete_soundtrack(movie_title, movie_year=None):
    """Remove uma trilha sonora do banco"""
    collection = get_mongo_collection("movie_soundtracks")
    
    try:
        cache_key = f"{movie_title}_{movie_year}" if movie_year else movie_title
        result = collection.delete_one({"cache_key": cache_key})
        
        if result.deleted_count == 1:
            return {"message": f"Trilha sonora de {movie_title} removida com sucesso"}, 200
        else:
            return {"message": f"Trilha sonora de {movie_title} não encontrada"}, 404
    except Exception as e:
        return {"error": "Erro ao deletar trilha sonora"}, 500
