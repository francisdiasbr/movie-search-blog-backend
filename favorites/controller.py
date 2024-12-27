import math
from config import get_mongo_collection

def get_favorited_movies(filters={}, sorters=["_id", -1], page=1, page_size=10, search_term=""):
    print(f"Iniciando busca de filmes favoritos com parâmetros:")
    print(f"Filtros: {filters}")
    print(f"Termo de busca: {search_term}")
    print(f"Página: {page}")
    print(f"Tamanho da página: {page_size}")

    try:
        # Obter a coleção do MongoDB
        collection = get_mongo_collection("favoritelist")
        print(f"Conexão com a coleção estabelecida")

        # Construir o filtro de busca
        search_filters = {}
        
        # Adicionar filtros existentes
        if filters:
            search_filters.update(filters)

        # Adicionar termo de busca se existir
        if search_term:
            search_filters["$or"] = [
                {"tconst": {"$regex": search_term, "$options": "i"}},
                {"originalTitle": {"$regex": search_term, "$options": "i"}},
                {"primaryTitle": {"$regex": search_term, "$options": "i"}},
                {"director": {"$regex": search_term, "$options": "i"}},
            ]
        
        print(f"Filtros finais: {search_filters}")

        # Contar total de documentos
        total_documents = collection.count_documents(search_filters)
        print(f"Total de documentos encontrados: {total_documents}")

        # Calcular skip para paginação
        skip = (page - 1) * page_size

        # Buscar documentos
        cursor = collection.find(search_filters)
        
        # Aplicar ordenação
        if sorters:
            cursor = cursor.sort(sorters[0], sorters[1])
        
        # Aplicar paginação
        cursor = cursor.skip(skip).limit(page_size)
        
        # Converter cursor para lista
        items = list(cursor)
        print(f"Número de itens retornados: {len(items)}")

        # Processar documentos
        for item in items:
            item["_id"] = str(item["_id"])
            if "startYear" in item and item["startYear"]:
                item["startYear"] = int(item["startYear"])

        # Buscar dados para filtros
        countries = collection.distinct("country")
        years = sorted([
            int(year) for year in collection.distinct("startYear") 
            if year is not None and str(year).isdigit()
        ])

        response = {
            "total_documents": total_documents,
            "entries": items,
            "countries": countries,
            "years": years,
            "current_page": page,
            "total_pages": math.ceil(total_documents / page_size),
            "page_size": page_size
        }

        print(f"Resposta final: {response}")
        return response, 200 if items else 404

    except Exception as e:
        print(f"Erro na busca: {e}")
        return {
            "status": 500,
            "message": "Erro interno do servidor",
            "error": str(e)
        }, 500 