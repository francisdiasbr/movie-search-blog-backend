def get_favorited_movies(filters={}, sorters=["_id", -1], page=1, page_size=10, search_term=""):
    print(f"Iniciando busca de filmes favoritos com parâmetros:")
    print(f"Filtros: {filters}")
    print(f"Termo de busca: {search_term}")
    print(f"Página: {page}")
    print(f"Tamanho da página: {page_size}")

    collection = get_mongo_collection("favoritelist")

    search_term = search_term or filters.get("search_term") or filters.get("tconst")
    print(f"Termo de busca final: {search_term}")

    if search_term:
        filters["$or"] = [
            {"tconst": search_term},
            {"originalTitle": {"$regex": search_term, "$options": "i"}},
            {"primaryTitle": {"$regex": search_term, "$options": "i"}},
            {"director": {"$regex": search_term, "$options": "i"}},
        ]
    
    print(f"Filtros finais: {filters}")

    try:
        total_documents = collection.count_documents(filters)
        print(f"Total de documentos encontrados: {total_documents}")

        skip = (page - 1) * page_size
        items = list(
            collection.find(filters)
            .sort(sorters[0], sorters[1])
            .skip(skip)
            .limit(page_size)
        )

        print(f"Número de itens retornados: {len(items)}")

        for item in items:
            item["_id"] = str(item["_id"])
            sanitize_movie_data(item)

        return {
            "total_documents": total_documents,
            "entries": items,
            "countries": collection.distinct("country"),
            "years": sorted([int(year) for year in collection.distinct("startYear") if year is not None])
        }, 200
    except Exception as e:
        print(f"Erro na busca: {e}")
        return {"status": 500, "message": "Erro interno do servidor"}, 500 