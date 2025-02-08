from config import get_mongo_collection

COLLECTION_NAME = "authoralreviewslist"

def search_write_reviews(filters, page=1, page_size=10):
    """Pesquisa opiniões pessoais com base em filtros e paginação"""
    try:
        write_reviews_collection = get_mongo_collection(COLLECTION_NAME)
        
        search_filters = {}
        text_fields = ["tconst", "primaryTitle", "content"]
        
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value
        
        total_documents = write_reviews_collection.count_documents(search_filters)
        skip = (page - 1) * page_size
        
        reviews = list(
            write_reviews_collection.find(search_filters)
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        for review in reviews:
            review["_id"] = str(review["_id"])
        
        return {
            "total_documents": total_documents,
            "entries": reviews
        }, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao pesquisar opiniões pessoais"}, 500


def get_write_review(tconst):
    """Recupera a primeira opinião pessoal para um filme específico"""
    try:
        write_reviews_collection = get_mongo_collection(COLLECTION_NAME)
        review = write_reviews_collection.find_one({"tconst": tconst})
        
        if review:
            review["_id"] = str(review["_id"])
            return {"data": review}, 200
        else:
            return {"status": 404, "message": "Opinião não encontrada"}, 404
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opinião pessoal"}, 500


def get_all_write_reviews():
    """Recupera todas as opiniões pessoais"""
    try:
        write_reviews_collection = get_mongo_collection(COLLECTION_NAME)
        reviews = list(write_reviews_collection.find({}))
        
        for review in reviews:
            review["_id"] = str(review["_id"])
        
        return {"data": reviews}, 200
    except Exception as e:
        print(f"Erro: {e}")
        return {"status": 500, "message": "Erro ao recuperar opiniões pessoais"}, 500