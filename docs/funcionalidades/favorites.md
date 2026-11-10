# Favoritos (`favorites`)

Arquivos: `favorites/routes.py`, `favorites/controller.py`, `favorites/models.py`. Prefixo:
`/api/favorites`. Coleção: `favoritelist`.

## O que faz

Busca na lista de filmes favoritados, com paginação, termo de busca livre e as listas de países e
anos que existem na coleção (para montar filtros na tela). O módulo só lê. Quem grava na coleção não
está neste repositório (não verificado).

## Rota

### `POST /api/favorites/search`

Corpo (JSON, objeto obrigatório; pode ser `{}`):

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtro do MongoDB, repassado como veio. |
| `page` | inteiro | `1` | Página. Mínimo 1. |
| `page_size` | inteiro | `10` | Itens por página. Mínimo 1. |
| `search_term` | string | `""` | Trecho procurado em `tconst`, `primaryTitle` e `director`, sem diferenciar maiúsculas. |

Exemplo:

```bash
curl -X POST http://localhost:5001/api/favorites/search \
  -H "Content-Type: application/json" \
  -d '{"search_term": "godard", "filters": {"country": "France"}, "page": 1, "page_size": 10}'
```

Resposta `200`:

```json
{
  "total_documents": 12,
  "entries": [
    {
      "_id": "66f0c0ffee0000000000abcd",
      "tconst": "tt0053472",
      "primaryTitle": "Breathless",
      "director": "Jean-Luc Godard",
      "country": "France",
      "startYear": 1960
    }
  ],
  "countries": ["France", "Italy"],
  "years": [1959, 1960, 1963],
  "current_page": 1,
  "total_pages": 2,
  "page_size": 10
}
```

| Código | Quando |
|---|---|
| `200` | Consulta feita. Sem resultados, `entries` vem vazio e `total_pages` vem `0`. |
| `400` | Corpo ausente, que não é JSON ou que não é objeto (`"Dados de entrada inválidos"`); `page` ou `page_size` que não convertem para inteiro, ou menores que 1 (`"Paginação inválida"`). |
| `500` | Banco indisponível (`{"status": 500, "message": "Erro de conexão com o banco de dados", "error": "Collection not found"}`) ou erro na consulta (`"Erro interno do servidor"`, com o texto da exceção em `error`). |

Esta é a rota com a validação de entrada mais completa da API.

## Passo a passo interno

1. A rota lê o corpo com `get_json(silent=True)` e converte `page` e `page_size` para inteiro.
2. O controller recusa paginação menor que 1.
3. Junta `filters` com o `$or` do `search_term`, se houver.
4. Conta o total, ordena por `_id` decrescente, aplica `skip` e `limit`.
5. Converte `_id` para string e tenta converter `startYear` para inteiro.
6. Calcula `countries` e `years` com `distinct` sobre a coleção inteira.

## Regras e casos de borda

- **`countries` e `years` ignoram a busca atual.** Eles refletem a coleção toda, não o resultado
  filtrado.
- **`years`** só traz valores feitos apenas de dígitos, convertidos para inteiro e em ordem crescente.
  Valores nulos ou não numéricos ficam de fora.
- **`startYear`** de cada item é convertido para inteiro quando possível. Se não der, o valor original
  é mantido.
- **Falha no `distinct`** não derruba a resposta: a lista correspondente vem vazia.
- **`search_term` é uma expressão regular.** Um termo que não seja uma expressão válida, como `(`,
  causa `500`.
- **`filters` é repassado ao MongoDB sem checagem.** Se `filters` trouxer a chave `$or`, ela é
  substituída pelo `$or` do `search_term` quando os dois vêm juntos.
- **Página além do fim** responde `200` com `entries` vazio.
- **Ordenação.** O controller aceita um parâmetro `sorters`, mas a rota não o repassa. Pela API, a
  ordem é sempre `_id` decrescente.
- **O modelo `FavoriteMovie` do Swagger** cita `soundtrack` e `wiki` como campos de um favorito. O
  controller não lê esses campos.
