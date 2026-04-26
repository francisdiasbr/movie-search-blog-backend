from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.exceptions import ClientError

from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BUCKET_NAME, get_mongo_collection

_s3_client = None


def _get_s3_client():
    global _s3_client
    if not _s3_client:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name="us-east-2",
        )
    return _s3_client


def _get_first_image_url(tconst):
    """Returns the URL of the first S3 image for a given tconst, or None."""
    try:
        s3 = _get_s3_client()
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"{tconst}/", MaxKeys=1)
        contents = response.get("Contents", [])
        if not contents:
            return None
        key = contents[0]["Key"]
        return f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{key}"
    except ClientError:
        return None


def get_home_cards(filters=None, page=1, page_size=10):
    """Returns paginated write-review cards with the first S3 image for each entry."""
    collection = get_mongo_collection("authoralreviewslist")
    if collection is None:
        return {"status": 500, "message": "Banco de dados indisponível"}, 500

    search_filters = {}
    if filters:
        text_fields = {"tconst", "primaryTitle"}
        for key, value in filters.items():
            if key in text_fields and isinstance(value, str):
                search_filters[key] = {"$regex": value, "$options": "i"}
            else:
                search_filters[key] = value

    try:
        total_documents = collection.count_documents(search_filters)
        skip = (page - 1) * page_size

        posts = list(
            collection.find(search_filters, {"tconst": 1, "primaryTitle": 1, "created_at": 1})
            .sort("_id", -1)
            .skip(skip)
            .limit(page_size)
        )

        for post in posts:
            post["_id"] = str(post["_id"])

        # Fetch first image for each post in parallel
        tconsts = [p["tconst"] for p in posts]
        image_map = {}
        with ThreadPoolExecutor(max_workers=min(len(tconsts), 5)) as executor:
            future_to_tconst = {executor.submit(_get_first_image_url, t): t for t in tconsts}
            for future in as_completed(future_to_tconst):
                tconst = future_to_tconst[future]
                try:
                    image_map[tconst] = future.result()
                except Exception:
                    image_map[tconst] = None

        entries = [
            {
                "_id": post["_id"],
                "tconst": post["tconst"],
                "primaryTitle": post.get("primaryTitle", ""),
                "created_at": post.get("created_at", ""),
                "imageUrl": image_map.get(post["tconst"]),
            }
            for post in posts
        ]

        return {"entries": entries, "total_documents": total_documents}, 200

    except Exception as e:
        return {"status": 500, "message": "Erro ao buscar cards"}, 500
