from config import get_mongo_collection, BUCKET_NAME
import boto3
from botocore.exceptions import ClientError
import logging
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def get_all_image_urls(bucket_name, tconst):
    """Retorna todas as URLs de imagens associadas a um post"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name='us-east-2'
        )

        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{tconst}/")
        images = []
        for obj in response.get('Contents', []):
            object_name = obj['Key']
            filename = object_name.split('/')[-1]
            
            # Adicionar log para debug
            print(f"Buscando tags para: {object_name}")

            # Busca as tags do objeto
            tag_response = s3_client.get_object_tagging(
                Bucket=bucket_name,
                Key=object_name
            )
            
            # Adicionar log para debug
            print(f"Tags encontradas: {tag_response}")
            
            # Procura pela tag de legenda
            subtitle = ""
            for tag in tag_response.get('TagSet', []):
                if tag['Key'] == 'subtitle':
                    subtitle = tag['Value']
                    break

            url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{object_name}"
            images.append({
                "url": url,
                "filename": filename,
                "subtitle": subtitle,
                "last_modified": obj['LastModified']
            })
        
        images.sort(key=lambda x: x['last_modified'])
        
        for image in images:
            del image['last_modified']
        
        return {"images": images}, 200

    except ClientError as e:
        print(f"Erro ao listar objetos no S3: {e}")
        return {"status": 500, "message": "Erro ao listar imagens"}, 500 
    

def get_image_url(bucket_name, tconst, filename):
    """Retorna a URL pública direta e a legenda de um arquivo no S3"""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name='us-east-2'
    )
    
    try:
        object_name = f"{tconst}/{filename}"
        
        # Busca as tags do objeto
        response = s3_client.get_object_tagging(
            Bucket=bucket_name,
            Key=object_name
        )
        
        # Procura pela tag de legenda
        subtitle = ""
        for tag in response.get('TagSet', []):
            if tag['Key'] == 'subtitle':
                subtitle = tag['Value']
                break
        
        url = f"https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_name}"
        return {
            "url": url,
            "filename": filename,
            "subtitle": subtitle
        }, 200
    except Exception as e:
        print(f"Erro ao buscar legenda: {e}")
        return {"status": 500, "message": "Erro ao buscar legenda"}, 500