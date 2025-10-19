import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from openai import OpenAI
from config import get_mongo_collection, OPENAI_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET


def get_movie_soundtrack(movie_title, movie_year=None, movie_director=None):
    """Busca a trilha sonora de um filme usando GPT e Spotify"""
    collection = get_mongo_collection("movie_soundtracks")
    
    try:
        # Primeiro tenta buscar no banco de dados
        cache_key = f"{movie_title}_{movie_year}" if movie_year else movie_title
        soundtrack_data = collection.find_one({"cache_key": cache_key})
        
        if soundtrack_data:
            # Converte ObjectId para string
            soundtrack_data["_id"] = str(soundtrack_data["_id"])
            return soundtrack_data, 200
        
        # Se não encontrou no banco, busca usando GPT + Spotify
        soundtrack_info = _get_soundtrack_with_gpt_and_spotify(movie_title, movie_year, movie_director)
        
        if soundtrack_info:
            # Adiciona cache_key para futuras consultas
            soundtrack_info["cache_key"] = cache_key
            
            # Salva no banco para futuras consultas
            result = collection.insert_one(soundtrack_info)
            soundtrack_info["_id"] = str(result.inserted_id)
            return soundtrack_info, 200
        
        return {"error": "Não foi possível encontrar a trilha sonora do filme"}, 404
        
    except Exception as e:
        print(f"Erro ao buscar trilha sonora: {e}")
        return {"error": "Erro ao buscar trilha sonora"}, 500


def _get_soundtrack_with_gpt_and_spotify(movie_title, movie_year=None, movie_director=None):
    """Usa GPT para identificar as principais músicas do filme e busca no Spotify"""
    try:
        # 1. Usa GPT para identificar as principais músicas do filme
        track_info = _get_track_info_with_gpt(movie_title, movie_year, movie_director)
        
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
        print(f"Erro ao processar trilha sonora: {e}")
        return None


def _get_track_info_with_gpt(movie_title, movie_year=None, movie_director=None):
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
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em cinema e música. Identifica trilhas sonoras icônicas de filmes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
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
        print(f"Erro ao gerar informações com GPT: {e}")
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
        print(f"Erro ao fazer parse manual: {e}")
        return None


def _search_tracks_on_spotify(tracks_info):
    """Busca as músicas no Spotify"""
    try:
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            print("Credenciais do Spotify não configuradas")
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
                print(f"Erro ao buscar música '{track_info['title']}': {e}")
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
        print(f"Erro ao buscar no Spotify: {e}")
        return []


def get_all_soundtracks():
    """Retorna todas as trilhas sonoras salvas no banco"""
    collection = get_mongo_collection("movie_soundtracks")
    
    try:
        soundtracks = list(collection.find({}, {"_id": 0}))
        return {"soundtracks": soundtracks}, 200
    except Exception as e:
        print(f"Erro ao buscar trilhas sonoras: {e}")
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
        print(f"Erro ao deletar trilha sonora: {e}")
        return {"error": "Erro ao deletar trilha sonora"}, 500
