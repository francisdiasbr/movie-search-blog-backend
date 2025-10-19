import requests
from openai import OpenAI
from config import get_mongo_collection, OPENAI_API_KEY


def get_director_info(director_name, movie_tconst=None):
    """Busca informações do diretor incluindo biografia e foto"""
    collection = get_mongo_collection("directors")
    
    try:
        # Primeiro tenta buscar no banco de dados
        director_data = collection.find_one({"name": director_name})
        
        if director_data:
            # Converte ObjectId para string
            director_data["_id"] = str(director_data["_id"])
            
            # Se não tem foto e temos o tconst do filme, tenta buscar a foto do IMDB
            if not director_data.get("photo") and movie_tconst:
                imdb_photo = _get_director_photo_from_imdb(director_name, movie_tconst)
                if imdb_photo:
                    # Atualiza a foto no banco
                    collection.update_one(
                        {"name": director_name},
                        {"$set": {"photo": imdb_photo}}
                    )
                    director_data["photo"] = imdb_photo
            
            return director_data, 200
        
        # Se não encontrou no banco, busca no TMDB
        tmdb_data = _fetch_director_from_tmdb(director_name)
        
        if tmdb_data:
            # Se não tem foto e temos o tconst do filme, tenta buscar a foto do IMDB
            if not tmdb_data.get("photo") and movie_tconst:
                imdb_photo = _get_director_photo_from_imdb(director_name, movie_tconst)
                if imdb_photo:
                    tmdb_data["photo"] = imdb_photo
            
            # Salva no banco para futuras consultas
            result = collection.insert_one(tmdb_data)
            tmdb_data["_id"] = str(result.inserted_id)
            return tmdb_data, 200
        
        # Se não encontrou no TMDB, gera biografia com OpenAI
        ai_bio = _generate_director_bio_with_ai(director_name)
        
        # Tenta buscar foto do IMDB se temos o tconst
        imdb_photo = None
        if movie_tconst:
            imdb_photo = _get_director_photo_from_imdb(director_name, movie_tconst)
        
        basic_data = {
            "name": director_name,
            "bio": ai_bio,
            "photo": imdb_photo
        }
        
        # Salva dados gerados pela IA no banco
        result = collection.insert_one(basic_data)
        basic_data["_id"] = str(result.inserted_id)
        return basic_data, 200
        
    except Exception as e:
        print(f"Erro ao buscar informações do diretor: {e}")
        return {"error": "Erro ao buscar informações do diretor"}, 500


def _fetch_director_from_tmdb(director_name):
    """Busca informações do diretor no TMDB"""
    try:
        # API Key do TMDB (você pode configurar isso nas variáveis de ambiente)
        tmdb_api_key = "YOUR_TMDB_API_KEY"  # Configure esta variável
        
        if tmdb_api_key == "YOUR_TMDB_API_KEY":
            # Se não tiver API key, retorna None para usar OpenAI
            return None
        
        # Busca pessoa no TMDB
        search_url = f"https://api.themoviedb.org/3/search/person"
        params = {
            "api_key": tmdb_api_key,
            "query": director_name,
            "language": "pt-BR"
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("results") and len(data["results"]) > 0:
            person = data["results"][0]  # Pega o primeiro resultado
            
            # Busca detalhes da pessoa
            person_id = person["id"]
            details_url = f"https://api.themoviedb.org/3/person/{person_id}"
            details_params = {
                "api_key": tmdb_api_key,
                "language": "pt-BR"
            }
            
            details_response = requests.get(details_url, params=details_params, timeout=10)
            details_response.raise_for_status()
            
            details_data = details_response.json()
            
            # Constrói a foto do diretor
            photo_url = None
            if details_data.get("profile_path"):
                photo_url = f"https://image.tmdb.org/t/p/w500{details_data['profile_path']}"
            
            return {
                "name": details_data.get("name", director_name),
                "bio": details_data.get("biography", f"Diretor de cinema conhecido por {director_name}."),
                "photo": photo_url
            }
        
        return None
        
    except requests.RequestException as e:
        print(f"Erro na requisição para TMDB: {e}")
        return None
    except Exception as e:
        print(f"Erro ao processar dados do TMDB: {e}")
        return None


def get_all_directors():
    """Retorna todos os diretores salvos no banco"""
    collection = get_mongo_collection("directors")
    
    try:
        directors = list(collection.find({}, {"_id": 0}))
        return {"directors": directors}, 200
    except Exception as e:
        print(f"Erro ao buscar diretores: {e}")
        return {"error": "Erro ao buscar diretores"}, 500


def _get_director_photo_from_imdb(director_name, movie_tconst):
    """Busca a foto do diretor do IMDB usando o tconst do filme"""
    try:
        # Primeiro, busca o ID do diretor na página do filme
        director_id = _get_director_id_from_movie_page(director_name, movie_tconst)
        
        if not director_id:
            return None
        
        # Agora busca a foto diretamente da página do diretor
        return _get_director_photo_from_director_page(director_id)
        
    except Exception as e:
        print(f"Erro ao buscar foto do diretor no IMDB: {e}")
        return None


def _get_director_id_from_movie_page(director_name, movie_tconst):
    """Extrai o ID do diretor da página do filme no IMDB"""
    try:
        # Constrói a URL da página do filme no IMDB
        imdb_url = f"https://www.imdb.com/title/{movie_tconst}/"
        
        # Faz a requisição para a página do filme
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(imdb_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        import re
        
        # Procura pelo link do diretor na página do filme
        # Padrão: <a href="/name/nm0000419/?ref_=tt_ov_1_1">Jean-Luc Godard</a>
        director_link_pattern = rf'<a[^>]*href="/name/(nm\d+)/[^"]*"[^>]*>{re.escape(director_name)}</a>'
        match = re.search(director_link_pattern, response.text, re.IGNORECASE)
        
        if match:
            return match.group(1)  # Retorna o ID (ex: nm0000419)
        
        return None
        
    except requests.RequestException as e:
        print(f"Erro na requisição para página do filme: {e}")
        return None
    except Exception as e:
        print(f"Erro ao extrair ID do diretor: {e}")
        return None


def _get_director_photo_from_director_page(director_id):
    """Busca a foto do diretor diretamente da página do diretor no IMDB"""
    try:
        # Constrói a URL da página do diretor no IMDB
        director_url = f"https://www.imdb.com/name/{director_id}/"
        
        # Faz a requisição para a página do diretor
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(director_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        import re
        
        # Procura pela foto principal do diretor na página
        # Padrão comum: https://m.media-amazon.com/images/M/[ID]_V1_UX[WIDTH]_CR0,0,[WIDTH],[HEIGHT]_AL_.jpg
        photo_patterns = [
            r'https://m\.media-amazon\.com/images/M/[^"]*_V1_UX\d+_CR0,0,\d+,\d+_AL_\.jpg',
            r'https://m\.media-amazon\.com/images/M/[^"]*\.jpg'
        ]
        
        for pattern in photo_patterns:
            matches = re.findall(pattern, response.text)
            if matches:
                # Retorna a primeira imagem encontrada (geralmente a principal)
                return matches[0]
        
        return None
        
    except requests.RequestException as e:
        print(f"Erro na requisição para página do diretor: {e}")
        return None
    except Exception as e:
        print(f"Erro ao processar dados da página do diretor: {e}")
        return None


def _generate_director_bio_with_ai(director_name):
    """Gera uma biografia rica do diretor usando OpenAI"""
    try:
        if not OPENAI_API_KEY:
            return f"Diretor de cinema conhecido por {director_name}."
        
        # Configura a API da OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
        Escreva uma biografia rica e detalhada sobre o diretor de cinema {director_name}. 
        A biografia deve ser similar ao estilo do Shazam para artistas musicais - envolvente, 
        informativa e que destaque a importância e contribuições do diretor para o cinema.
        
        Inclua:
        - Estilo cinematográfico único
        - Filmes mais importantes e influentes
        - Técnicas inovadoras ou características marcantes
        - Impacto na indústria cinematográfica
        - Prêmios ou reconhecimentos importantes
        - Influências e legado
        
        A biografia deve ter entre 150-250 palavras, ser em português brasileiro, 
        e ter um tom respeitoso e informativo, similar ao que se vê em plataformas 
        como Shazam para artistas musicais.
        
        Se não souber informações específicas sobre o diretor, seja honesto mas 
        mantenha um tom positivo sobre sua contribuição para o cinema.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em cinema e escreve biografias envolventes sobre diretores de cinema."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        bio = response.choices[0].message.content.strip()
        return bio
        
    except Exception as e:
        print(f"Erro ao gerar biografia com OpenAI: {e}")
        return f"Diretor de cinema conhecido por {director_name}. Um cineasta que contribuiu significativamente para a arte cinematográfica com seu estilo único e visão criativa."


def delete_director(director_name):
    """Remove um diretor do banco"""
    collection = get_mongo_collection("directors")
    
    try:
        result = collection.delete_one({"name": director_name})
        
        if result.deleted_count == 1:
            return {"message": f"Diretor {director_name} removido com sucesso"}, 200
        else:
            return {"message": f"Diretor {director_name} não encontrado"}, 404
    except Exception as e:
        print(f"Erro ao deletar diretor: {e}")
        return {"error": "Erro ao deletar diretor"}, 500
