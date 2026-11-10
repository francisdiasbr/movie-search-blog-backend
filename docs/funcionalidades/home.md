# Página inicial (`home`)

Arquivos: `home/routes.py`, `home/controller.py`. Prefixo: `/api/home`.

## O que faz

Entrega os cards da página inicial do blog. Cada card é uma resenha autoral reduzida a título,
identificador, data e a URL de uma imagem. O objetivo é montar a página com uma única requisição, sem
trazer o texto completo das resenhas.

## Rota

### `POST /api/home/cards`

Corpo (JSON, todos os campos opcionais):

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtros sobre a coleção `authoralreviewslist`. |
| `page` | inteiro | `1` | Página. |
| `page_size` | inteiro | `10` | Itens por página. |

Corpo ausente, sem `Content-Type` JSON ou que não seja um objeto é tratado como `{}`.

Exemplo:

```bash
curl -X POST http://localhost:5001/api/home/cards \
  -H "Content-Type: application/json" \
  -d '{"filters": {"primaryTitle": "breath"}, "page": 1, "page_size": 10}'
```

Resposta `200`:

```json
{
  "entries": [
    {
      "_id": "66f0c0ffee0000000000abcd",
      "tconst": "tt0053472",
      "primaryTitle": "Breathless",
      "created_at": "2024-09-22T14:03:11",
      "imageUrl": "https://<bucket>.s3.us-east-2.amazonaws.com/tt0053472/01.jpg"
    }
  ],
  "total_documents": 1
}
```

| Código | Quando |
|---|---|
| `200` | Sempre que a consulta funciona, mesmo sem resultados (`entries` vazio, `total_documents` zero). |
| `500` | Banco indisponível (`{"status": 500, "message": "Banco de dados indisponível"}`) ou qualquer erro na consulta (`"Erro ao buscar cards"`). |

## Passo a passo interno

1. Monta os filtros. Para `tconst` e `primaryTitle`, valor string vira busca por trecho sem
   diferenciar maiúsculas. Os outros filtros são igualdade exata.
2. Conta os documentos que casam (`total_documents`).
3. Busca a página, ordenada por `_id` decrescente, com projeção de `tconst`, `primaryTitle` e
   `created_at`. O texto da resenha não é lido.
4. Monta a lista de `tconst` da página, sem repetições e sem valores vazios.
5. Para cada `tconst`, chama o S3 em paralelo (`ThreadPoolExecutor` com até 5 threads) pedindo um
   único objeto sob o prefixo `<tconst>/` (`list_objects_v2` com `MaxKeys=1`).
6. Monta cada card com a URL `https://<BUCKET_NAME>.s3.us-east-2.amazonaws.com/<chave>`.

## Regras e casos de borda

- **Qual imagem é "a primeira".** É o primeiro objeto que o S3 devolve na listagem do prefixo. O
  módulo `images` ordena por data de modificação; o `home` não ordena. As duas rotas podem apontar
  imagens diferentes como primeira.
- **Resenha sem imagem.** `imageUrl` vem `null`.
- **Resenha sem `tconst`.** Ganha card, com `tconst` e `imageUrl` nulos. Nenhuma chamada ao S3 é feita
  por ela.
- **Falha do S3 em uma resenha.** Não derruba a resposta. O card daquela resenha sai com
  `imageUrl: null` e os outros seguem normais. Isso vale para `ClientError` e para qualquer outra
  exceção.
- **Página sem resenhas.** O executor de threads não é criado quando não há `tconst` (ele recusa zero
  threads).
- **`created_at`.** Se o campo é uma data do BSON, sai como texto ISO. Se é string, sai como está. Se
  não existe, sai como string vazia. `primaryTitle` ausente também sai como string vazia.
- **`page` e `page_size` não são validados.** Um valor que não seja número (por exemplo `"2"`) causa
  erro na conta do `skip` e a resposta é `500`. O efeito de `page` menor que 1 em um MongoDB real é
  não verificado.
- **Cliente S3.** É criado uma vez por processo e reutilizado.
