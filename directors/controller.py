import requests
from openai import OpenAI
from config import get_mongo_collection, OPENAI_API_KEY, OPENAI_MODEL
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_director_info(director_name, movie_tconst=None, language="pt"):
    """Busca informações do diretor incluindo biografia e foto.

    A bio gravada é sempre a canônica, em português; outro idioma é traduzido
    na resposta, sem persistir.
    """
    collection = get_mongo_collection("directors")
    if collection is None:
        return {"error": "Erro ao buscar informações do diretor"}, 500

    try:
        # Verifica se há múltiplos diretores separados por vírgula
        if "," in director_name:
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
                        {"name": director_name}, {"$set": {"photo": imdb_photo}}
                    )
                    director_data["photo"] = imdb_photo

            # Gera biografia no idioma solicitado se necessário
            if language != "pt" and director_data.get("bio"):
                # Tradução simples sem cache
                director_data["bio"] = _translate_director_bio(
                    director_data["bio"], language
                )

            return director_data, 200

        # Se não encontrou no banco, gera a biografia (em português) com OpenAI
        ai_bio = _generate_director_bio_with_ai(director_name)

        # Tenta buscar foto do IMDB se temos o tconst
        imdb_photo = None
        if movie_tconst:
            imdb_photo = _get_director_photo_from_imdb(director_name, movie_tconst)

        if not ai_bio:
            # Sem biografia real: responde com o texto genérico, sem gravar,
            # para tentar de novo na próxima consulta
            return _placeholder_director(director_name, language, imdb_photo), 200

        basic_data = {"name": director_name, "bio": ai_bio, "photo": imdb_photo}

        # Salva dados gerados pela IA no banco
        result = collection.insert_one(basic_data)
        basic_data["_id"] = str(result.inserted_id)

        if language != "pt":
            basic_data["bio"] = _translate_director_bio(ai_bio, language)

        return basic_data, 200

    except Exception as e:
        return {"error": "Erro ao buscar informações do diretor"}, 500


def _placeholder_director(director_name, language="pt", photo=None):
    """Diretor com biografia genérica; `placeholder` avisa que nada foi gravado."""
    bio = (
        f"Diretor de cinema conhecido por {director_name}."
        if language == "pt"
        else f"Film director known for {director_name}."
    )
    return {"name": director_name, "bio": bio, "photo": photo, "placeholder": True}


def _get_multiple_directors_info(directors_string, movie_tconst=None, language="pt"):
    """Busca informações para múltiplos diretores"""
    try:
        # Separa os diretores por vírgula e remove espaços extras
        director_names = [name.strip() for name in directors_string.split(",")]

        directors_info = []

        for director_name in director_names:
            if director_name:  # Verifica se o nome não está vazio
                # Busca informações para cada diretor individualmente
                director_info, status_code = get_director_info(
                    director_name, movie_tconst, language
                )

                if status_code == 200 and director_info:
                    directors_info.append(director_info)
                else:
                    # Se não encontrou informações, cria um diretor básico
                    directors_info.append(
                        _placeholder_director(director_name, language)
                    )

        # Retorna informações combinadas de todos os diretores
        if directors_info:
            combined_info = {
                "name": directors_string,  # Nome completo com todos os diretores
                "bio": _create_combined_directors_bio(directors_info, language),
                # Usa a foto do primeiro diretor
                "photo": directors_info[0].get("photo"),
                "directors": directors_info,  # Lista de todos os diretores individuais
            }
            if any(director.get("placeholder") for director in directors_info):
                combined_info["placeholder"] = True
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(imdb_url, headers=headers, timeout=3)
        response.raise_for_status()

        import re

        # Procura pelo link do diretor na página do filme
        # Padrão: <a href="/name/nm0000419/?ref_=tt_ov_1_1">Jean-Luc Godard</a>
        director_link_pattern = (
            rf'<a[^>]*href="/name/(nm\d+)/[^"]*"[^>]*>{re.escape(director_name)}</a>'
        )
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(director_url, headers=headers, timeout=3)
        response.raise_for_status()

        import re

        # Procura pela foto principal do diretor na página
        # Padrão comum: https://m.media-amazon.com/images/M/[ID]_V1_UX[WIDTH]_CR0,0,[WIDTH],[HEIGHT]_AL_.jpg
        photo_patterns = [
            r'https://m\.media-amazon\.com/images/M/[^"]*_V1_UX\d+_CR0,0,\d+,\d+_AL_\.jpg',
            r'https://m\.media-amazon\.com/images/M/[^"]*\.jpg',
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


def _generate_director_bio_with_ai(director_name):
    """Gera a biografia do diretor, em português, usando OpenAI.

    Devolve None quando não há chave ou a chamada falha.
    """
    try:
        if not OPENAI_API_KEY:
            return None

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
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em cinema e escreve biografias envolventes sobre diretores de cinema.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,  # Reduzido para resposta mais rápida
            temperature=0.7,
            timeout=5,  # Timeout de 5 segundos
        )

        return response.choices[0].message.content.strip() or None

    except Exception as e:
        return None


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
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator specializing in film and entertainment content.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.3,
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
