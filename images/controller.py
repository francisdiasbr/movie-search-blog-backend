import boto3
from botocore.exceptions import ClientError

from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BUCKET_NAME

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


def get_all_image_urls(bucket_name, tconst):
    """Retorna todas as URLs de imagens associadas a um post"""
    try:
        s3 = _get_s3_client()
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=f"{tconst}/")
        images = []

        for obj in response.get("Contents", []):
            object_name = obj["Key"]
            filename = object_name.split("/")[-1]

            tag_response = s3.get_object_tagging(Bucket=bucket_name, Key=object_name)

            subtitle_pt = ""
            subtitle_en = ""
            for tag in tag_response.get("TagSet", []):
                if tag["Key"] == "subtitle_pt":
                    subtitle_pt = tag["Value"]
                elif tag["Key"] == "subtitle_en":
                    subtitle_en = tag["Value"]

            url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{object_name}"
            images.append(
                {
                    "url": url,
                    "filename": filename,
                    "subtitle_pt": subtitle_pt,
                    "subtitle_en": subtitle_en,
                    "last_modified": obj["LastModified"],
                }
            )

        images.sort(key=lambda x: x["last_modified"])
        for image in images:
            del image["last_modified"]

        return {"images": images}, 200

    except ClientError:
        return {"status": 500, "message": "Erro ao listar imagens"}, 500


def get_image_url(bucket_name, tconst, filename):
    """Retorna a URL pública e legendas de um arquivo no S3"""
    try:
        s3 = _get_s3_client()
        object_name = f"{tconst}/{filename}"

        response = s3.get_object_tagging(Bucket=bucket_name, Key=object_name)

        subtitle_pt = ""
        subtitle_en = ""
        for tag in response.get("TagSet", []):
            if tag["Key"] == "subtitle_pt":
                subtitle_pt = tag["Value"]
            elif tag["Key"] == "subtitle_en":
                subtitle_en = tag["Value"]

        url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{object_name}"
        return {
            "url": url,
            "filename": filename,
            "subtitle_pt": subtitle_pt,
            "subtitle_en": subtitle_en,
        }, 200

    except Exception:
        return {"status": 500, "message": "Erro ao buscar imagem"}, 500
