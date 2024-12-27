from config import get_mongo_collection, BUCKET_NAME
import boto3
from botocore.exceptions import ClientError
import logging
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

def get_all_image_urls(tconst):
    """Retorna todas as URLs de imagens associadas a um post"""
    try:
        # Configurar o cliente S3 usando as credenciais do config.py
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name='us-east-2'  # Certifique-se de que esta é a região correta
        )

        # Lista todos os objetos no bucket que começam com o prefixo tconst
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"{tconst}/")
        images = []
        for obj in response.get('Contents', []):
            object_name = obj['Key']
            filename = object_name.split('/')[-1]
            
            url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{object_name}"
            images.append({
                "url": url,
                "filename": filename,
                "last_modified": obj['LastModified']
            })
        
        images.sort(key=lambda x: x['last_modified'])
        
        for image in images:
            del image['last_modified']
        
        return {"images": images}, 200

    except ClientError as e:
        print(f"Erro ao listar objetos no S3: {e}")
        return {"status": 500, "message": "Erro ao listar imagens"}, 500 