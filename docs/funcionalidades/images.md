# Imagens (`images`)

Arquivos: `images/routes.py`, `images/controller.py`. Prefixo: `/api/images`. Armazenamento: bucket
S3 definido em `BUCKET_NAME`, região `us-east-2`.

## O que faz

Lista as imagens de um filme guardadas no S3 e devolve, para cada uma, a URL direta e as legendas em
português e inglês. A API só lê: o envio das imagens e a gravação das legendas acontecem fora deste
repositório (não verificado).

## Como as imagens estão organizadas

- Cada filme tem uma "pasta" no bucket: a chave do objeto é `<tconst>/<arquivo>`.
- As legendas ficam nas tags do objeto: `subtitle_pt` e `subtitle_en`.
- A URL é montada por texto: `https://<bucket>.s3.us-east-2.amazonaws.com/<tconst>/<arquivo>`. Não é
  uma URL assinada. Ela só abre se o objeto tiver leitura pública; a política do bucket é não
  verificada.

## Rotas

### `GET /api/images/<tconst>`

Resposta `200`:

```json
{
  "images": [
    {
      "url": "https://<bucket>.s3.us-east-2.amazonaws.com/tt0053472/01.jpg",
      "filename": "01.jpg",
      "subtitle_pt": "Cena na Champs-Élysées",
      "subtitle_en": "Champs-Élysées scene"
    }
  ]
}
```

| Código | Quando |
|---|---|
| `200` | Listagem feita. Filme sem imagens devolve `{"images": []}`. |
| `500` | Qualquer falha do S3: `{"status": 500, "message": "Erro ao listar imagens"}`. |

### `GET /api/images/<tconst>/<filename>`

Resposta `200`:

```json
{
  "url": "https://<bucket>.s3.us-east-2.amazonaws.com/tt0053472/01.jpg",
  "filename": "01.jpg",
  "subtitle_pt": "Cena na Champs-Élysées",
  "subtitle_en": ""
}
```

| Código | Quando |
|---|---|
| `200` | O S3 devolveu as tags do objeto. |
| `404` | O S3 respondeu `ClientError` com código `NoSuchKey`, `NotFound` ou `404`: `{"status": 404, "message": "Imagem não encontrada"}`. |
| `500` | Qualquer outra falha: `{"status": 500, "message": "Erro ao buscar imagem"}`. |

## Passo a passo interno

Listagem:

1. `list_objects_v2` com o prefixo `<tconst>/`.
2. Para cada objeto, `get_object_tagging` para ler as legendas. É uma chamada ao S3 por imagem, em
   sequência.
3. Ordena as imagens por data de modificação, da mais antiga para a mais nova.
4. Remove a data de modificação antes de responder.

Imagem única:

1. `get_object_tagging` na chave `<tconst>/<filename>`.
2. Monta a URL e devolve as legendas.

## Regras e casos de borda

- **Ordem.** A listagem sai por data de modificação crescente, não por nome de arquivo.
- **Legenda ausente** vem como string vazia.
- **A existência da imagem é inferida da leitura das tags.** Não há chamada separada para conferir o
  objeto.
- **A listagem não pagina.** O código faz uma única chamada a `list_objects_v2` e não trata
  continuação. O limite de objetos por chamada é o do S3 (não verificado aqui).
- **Um erro em qualquer imagem derruba a listagem inteira** com `500`, porque o `try` envolve o laço
  todo.
- **O cliente S3** é criado uma vez por processo. O módulo `home` mantém o seu próprio cliente, com
  código igual.
- **`BUCKET_NAME` é lido na importação** de `images/routes.py`.
