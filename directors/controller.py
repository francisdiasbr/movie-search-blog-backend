import requests
from openai import OpenAI
from config import get_mongo_collection, OPENAI_API_KEY
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_director_info(director_name, movie_tconst=None, language="pt"):
    """Busca informações do diretor incluindo biografia e foto"""
    collection = get_mongo_collection("directors")
    
    try:
        # Verifica se há múltiplos diretores separados por vírgula
        if ',' in director_name:
            return _get_multiple_directors_info(director_name, movie_tconst, language)
        
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
            
            # Gera biografia no idioma solicitado se necessário
            if language != "pt" and director_data.get("bio"):
                # Tradução simples sem cache
                director_data["bio"] = _translate_director_bio(director_data["bio"], language)
            
            return director_data, 200
        
        # Se não encontrou no banco, busca no TMDB
        tmdb_data = _fetch_director_from_tmdb(director_name, language)
        
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
        ai_bio = _generate_director_bio_with_ai(director_name, language)
        
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
        return {"error": "Erro ao buscar informações do diretor"}, 500


def _get_multiple_directors_info(directors_string, movie_tconst=None, language="pt"):
    """Busca informações para múltiplos diretores"""
    try:
        # Separa os diretores por vírgula e remove espaços extras
        director_names = [name.strip() for name in directors_string.split(',')]
        
        directors_info = []
        
        for director_name in director_names:
            if director_name:  # Verifica se o nome não está vazio
                # Busca informações para cada diretor individualmente
                director_info, status_code = get_director_info(director_name, movie_tconst, language)
                
                if status_code == 200 and director_info:
                    directors_info.append(director_info)
                else:
                    # Se não encontrou informações, cria um diretor básico
                    basic_director = {
                        "name": director_name,
                        "bio": f"Diretor de cinema conhecido por {director_name}." if language == "pt" else f"Film director known for {director_name}.",
                        "photo": None
                    }
                    directors_info.append(basic_director)
        
        # Retorna informações combinadas de todos os diretores
        if directors_info:
            combined_info = {
                "name": directors_string,  # Nome completo com todos os diretores
                "bio": _create_combined_directors_bio(directors_info, language),
                "photo": directors_info[0].get("photo") if directors_info else None,  # Usa a foto do primeiro diretor
                "directors": directors_info  # Lista de todos os diretores individuais
            }
            return combined_info, 200
        else:
            return {"error": "Nenhum diretor encontrado"}, 404
            
    except Exception as e:
        return {"error": "Erro ao buscar informações dos diretores"}, 500


def _create_combined_directors_bio(directors_info, language="pt"):
    """Cria uma biografia combinada para múltiplos diretores"""
    try:
        if language == "pt":
            bio_parts = []
            for i, director in enumerate(directors_info):
                name = director.get("name", "")
                bio = director.get("bio", "")
                
                if i == 0:
                    bio_parts.append(f"{name}: {bio}")
                else:
                    bio_parts.append(f"\n\n{name}: {bio}")
            
            return "".join(bio_parts)
        else:
            bio_parts = []
            for i, director in enumerate(directors_info):
                name = director.get("name", "")
                bio = director.get("bio", "")
                
                if i == 0:
                    bio_parts.append(f"{name}: {bio}")
                else:
                    bio_parts.append(f"\n\n{name}: {bio}")
            
            return "".join(bio_parts)
            
    except Exception as e:
        # Fallback simples
        director_names = [d.get("name", "") for d in directors_info]
        if language == "pt":
            return f"Diretores de cinema: {', '.join(director_names)}."
        else:
            return f"Film directors: {', '.join(director_names)}."


def _fetch_director_from_tmdb(director_name, language="pt"):
    """Busca informações do diretor no TMDB"""
    try:
        # API Key do TMDB (você pode configurar isso nas variáveis de ambiente)
        tmdb_api_key = "YOUR_TMDB_API_KEY"  # Configure esta variável
        
        if tmdb_api_key == "YOUR_TMDB_API_KEY":
            # Se não tiver API key, retorna None para usar OpenAI
            return None
        
        # Define o idioma para o TMDB
        tmdb_language = "pt-BR" if language == "pt" else "en-US"
        
        # Busca pessoa no TMDB
        search_url = f"https://api.themoviedb.org/3/search/person"
        params = {
            "api_key": tmdb_api_key,
            "query": director_name,
            "language": tmdb_language
        }
        
        response = requests.get(search_url, params=params, timeout=3)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("results") and len(data["results"]) > 0:
            person = data["results"][0]  # Pega o primeiro resultado
            
            # Busca detalhes da pessoa
            person_id = person["id"]
            details_url = f"https://api.themoviedb.org/3/person/{person_id}"
            details_params = {
                "api_key": tmdb_api_key,
                "language": tmdb_language
            }
            
            details_response = requests.get(details_url, params=details_params, timeout=3)
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
        return None
    except Exception as e:
        return None


def get_all_directors():
    """Retorna todos os diretores salvos no banco"""
    collection = get_mongo_collection("directors")
    
    try:
        directors = list(collection.find({}, {"_id": 0}))
        return {"directors": directors}, 200
    except Exception as e:
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
        
        response = requests.get(imdb_url, headers=headers, timeout=3)
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
        return None
    except Exception as e:
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
        
        response = requests.get(director_url, headers=headers, timeout=3)
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
        return None
    except Exception as e:
        return None


def _generate_director_bio_with_ai(director_name, language="pt"):
    """Gera uma biografia rica do diretor usando OpenAI"""
    try:
        if not OPENAI_API_KEY:
            if language == "en":
                return f"Film director known for {director_name}."
            return f"Diretor de cinema conhecido por {director_name}."
        
        # Configura a API da OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        if language == "en":
            prompt = f"""
            Write a rich and detailed biography about film director {director_name}. 
            The biography should be similar to Shazam's style for musical artists - engaging, 
            informative and highlighting the importance and contributions of the director to cinema.
            
            Include:
            - Unique cinematic style
            - Most important and influential films
            - Innovative techniques or distinctive characteristics
            - Impact on the film industry
            - Important awards or recognitions
            - Influences and legacy
            
            The biography should be between 150-250 words, be in English, 
            and have a respectful and informative tone, similar to what you see on platforms 
            like Shazam for musical artists.
            
            If you don't know specific information about the director, be honest but 
            maintain a positive tone about their contribution to cinema.
            """
        else:
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
        
        system_message = "You are a cinema expert and write engaging biographies about film directors." if language == "en" else "Você é um especialista em cinema e escreve biografias envolventes sobre diretores de cinema."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,  # Reduzido para resposta mais rápida
            temperature=0.7,
            timeout=5  # Timeout de 5 segundos
        )
        
        bio = response.choices[0].message.content.strip()
        return bio
        
    except Exception as e:
        if language == "en":
            return f"Film director known for {director_name}. A filmmaker who contributed significantly to the art of cinema with their unique style and creative vision."
        return f"Diretor de cinema conhecido por {director_name}. Um cineasta que contribuiu significativamente para a arte cinematográfica com seu estilo único e visão criativa."


def _translate_director_bio(bio, language):
    """Traduz a biografia do diretor para o idioma solicitado"""
    try:
        if not OPENAI_API_KEY or language == "pt":
            return bio
        
        # Configura a API da OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
        Translate the following film director biography to English. 
        Maintain the same style, tone, and level of detail. 
        Keep it engaging and informative, similar to Shazam's style for musical artists.
        
        Biography to translate:
        {bio}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator specializing in film and entertainment content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.3
        )
        
        translated_bio = response.choices[0].message.content.strip()
        return translated_bio
        
    except Exception as e:
        return bio  # Retorna a biografia original em caso de erro


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
        return {"error": "Erro ao deletar diretor"}, 500
