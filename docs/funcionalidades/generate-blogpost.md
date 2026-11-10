# Posts do blog (`generate_blogpost`)

Arquivos: `generate_blogpost/routes.py`, `generate_blogpost/controller.py`,
`generate_blogpost/models.py`. Prefixo: `/api/generate-blogpost`. Coleção: `blogposts`.

## O que faz

Entrega os posts do blog guardados na coleção `blogposts`: busca paginada e leitura de um post por
`tconst`.

**Este módulo não gera nada e não chama a OpenAI.** Apesar do nome da pasta e da descrição do
namespace no Swagger ("geração de postagens de blog sobre filmes"), o código atual só lê do MongoDB.
Não há rota de criação, edição ou remoção. Quem grava os posts na coleção não está neste repositório
(não verificado).

## Rotas

### `POST /api/generate-blogpost/search`

Corpo (JSON, objeto obrigatório):

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtros. |
| `page` | inteiro | `1` | Página. |
| `page_size` | inteiro | `10` | Itens por página. |

Resposta `200`:

```json
{
  "total_documents": 1,
  "entries": [
    {"_id": "66f0c0ffee0000000000abcd", "tconst": "tt0053472", "primaryTitle": "Breathless"}
  ]
}
```

Cada item é o documento inteiro, com `_id` em string, do mais novo para o mais antigo.

| Código | Quando |
|---|---|
| `200` | Existe ao menos um documento que casa com os filtros. |
| `400` | O corpo JSON não é um objeto: `{"status": 400, "message": "Dados de entrada inválidos"}`. |
| `404` | Nenhum documento casa com os filtros. O corpo ainda traz `{"total_documents": 0, "entries": []}`. |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | Erro na consulta: `{"status": 500, "message": "<texto da exceção>"}`. |

### `GET /api/generate-blogpost/<tconst>`

| Código | Corpo |
|---|---|
| `200` | `{"data": { ...documento do post... }}` |
| `404` | `{"status": "erro", "mensagem": "Post não encontrado"}` |
| `500` | `{"status": "erro", "mensagem": "<texto da exceção>"}` |

## Regras de filtro

Campos de texto, com busca por trecho sem diferenciar maiúsculas: `tconst`, `primaryTitle`, `title`,
`introduction`, `historical_context`, `cultural_importance`, `technical_analysis` e `conclusion`.
Qualquer outro filtro é igualdade exata.

## Casos de borda

- **Busca vazia é `404`, não `200`.** É a única busca paginada da API com esse comportamento. As
  outras respondem `200` com lista vazia.
- **Página além do fim é `200`.** O código decide o status por `total_documents`. Se há resultados,
  mas a página pedida não tem nenhum, a resposta é `200` com `entries` vazio.
- **O formato de erro do `GET` é diferente do resto da API:** usa `status: "erro"` e `mensagem`.
- **`page` e `page_size` não são validados.** Um valor string causa `500` com a mensagem da exceção
  do Python.
- **Os modelos do Swagger** (`BlogPost`, `BlogPostSearch`) são só documentação. O modelo `BlogPost`
  lista `content`, `created_at`, `images`, `poster_url`, `references` e `soundtrack`, mas os campos
  de texto da busca são outros (`introduction`, `conclusion` etc.). Qual das duas formas os
  documentos reais têm é não verificado.
