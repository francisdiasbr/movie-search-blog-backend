import math
from config import get_mongo_collection

def get_favorited_movies(filters={}, sorters=["_id", -1], page=1, page_size=10, search_term=""):
    try:
        collection = get_mongo_collection("favoritelist")
        
        if collection is None:
            return {
                "status": 500,
                "message": "Erro de conexão com o banco de dados",
                "error": "Collection not found"
            }, 500

        search_filters = {}
        
        if filters:
            search_filters.update(filters)

        if search_term:
            search_filters["$or"] = [
                {"tconst": {"$regex": search_term, "$options": "i"}},
                {"primaryTitle": {"$regex": search_term, "$options": "i"}},
                {"director": {"$regex": search_term, "$options": "i"}},
            ]

        total_documents = collection.count_documents(search_filters)
        skip = (page - 1) * page_size

        cursor = collection.find(search_filters)
        
        if sorters:
            cursor = cursor.sort(sorters[0], sorters[1])
        
        cursor = cursor.skip(skip).limit(page_size)
        items = list(cursor)

        for item in items:
            item["_id"] = str(item["_id"])
            if "startYear" in item and item["startYear"]:
                try:
                    item["startYear"] = int(item["startYear"])
                except (ValueError, TypeError):
                    # Se não conseguir converter, mantém o valor original
                    pass

        try:
            countries = collection.distinct("country")
        except Exception:
            countries = []
        
        try:
            years = sorted([
                int(year) for year in collection.distinct("startYear") 
                if year is not None and str(year).isdigit()
            ])
        except Exception:
            years = []

        response = {
            "total_documents": total_documents,
            "entries": items,
            "countries": countries,
            "years": years,
            "current_page": page,
            "total_pages": math.ceil(total_documents / page_size),
            "page_size": page_size
        }

        return response, 200 if items else 404

    except Exception as e:
        return {
            "status": 500,
            "message": "Erro interno do servidor",
            "error": str(e)
        }, 500 