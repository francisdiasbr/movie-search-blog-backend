from config import get_mongo_collection

COLLECTION_NAME = "personal_opinions"

def search_personal_opinions(filters, page=1, page_size=10):
    """Pesquisa opiniões pessoais com base em filtros e paginação"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        
        search_filters = {}
        text_fields = ["tconst", "opinion", "rate"]
        
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value
        
        total_documents = personal_opinions_collection.count_documents(search_filters)
        skip = (page - 1) * page_size
        
        opinions = list(
            personal_opinions_collection.find(search_filters)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        for opinion in opinions:
            opinion["_id"] = str(opinion["_id"])
        
        return {
            "total_documents": total_documents,
            "entries": opinions
        }, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao pesquisar opiniões pessoais"}, 500


def get_personal_opinion(tconst):
    """Recupera a primeira opinião pessoal para um filme específico"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        opinion = personal_opinions_collection.find_one({"tconst": tconst})
        
        if opinion:
            opinion["_id"] = str(opinion["_id"])
            return {"data": opinion}, 200
        else:
            return {"status": 404, "message": "Opinião não encontrada"}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opinião pessoal"}, 500


def get_all_personal_opinions():
    """Recupera todas as opiniões pessoais"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        opinions = list(personal_opinions_collection.find({}))
        
        for opinion in opinions:
            opinion["_id"] = str(opinion["_id"])
        
        return {"data": opinions}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opiniões pessoais"}, 500


def update_personal_opinion(tconst, update_data):
    """Atualiza uma opinião pessoal existente"""
    try:
        personal_opinions_collection = get_mongo_collection(COLLECTION_NAME)
        
        # Verifica se a opinião existe
        existing_opinion = personal_opinions_collection.find_one({"tconst": tconst})
        if not existing_opinion:
            return {"status": 404, "message": "Opinião não encontrada"}, 404
        
        # Atualiza apenas os campos permitidos
        allowed_fields = ["opinion", "rate", "enjoying"]
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        result = personal_opinions_collection.update_one(
            {"tconst": tconst},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0:
            return {"status": 200, "message": "Opinião atualizada com sucesso"}, 200
        return {"status": 400, "message": "Nenhuma alteração realizada"}, 400
        
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao atualizar opinião pessoal"}, 500