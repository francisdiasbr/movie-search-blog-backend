# Recomendações (`recommendations`)

Arquivos: `recommendations/routes.py`, `recommendations/controller.py`. Prefixo:
`/api/recommendations`. Coleção: `recommendations`.

## O que faz

Mantém a lista de filmes recomendados do blog, na ordem de uma watchlist. É o único módulo de
conteúdo com escrita completa pela API: adiciona um filme, adiciona vários de uma vez, remove um e
limpa tudo. Ao adicionar, pode disparar a [pré-população](prepopulate.md) de diretor e trilha.

A coleção `recommendations` também é a fonte de dados de filme para o
[detalhe do filme](movie-detail-cache.md) e para a pré-população.

## Rotas

### `GET /api/recommendations/random`

Devolve **todas** as recomendações, em ordem crescente de `position`.

O nome da rota é histórico. Nada é sorteado nem amostrado: a lista é completa e a ordem é
determinística. O nome foi mantido porque o frontend consome `/random` e exibe a lista na ordem em
que recebe (isso está registrado na docstring do controller).

Resposta `200`:

```json
{
  "data": [
    {"_id": "66f0...", "tconst": "tt0053472", "title": "Breathless", "year": "1960", "director": "Jean-Luc Godard", "position": 1}
  ],
  "total": 1
}
```

| Código | Corpo |
|---|---|
| `200` | Lista e total. Coleção vazia devolve `{"data": [], "total": 0}`. |
| `500` | `{"status": 500, "message": "Erro ao buscar recomendações"}` |

### `GET /api/recommendations/all`

Query string:

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `page` | inteiro | `1` | Página. |
| `page_size` | inteiro | `10` | Itens por página. |
| `search_term` | string | `""` | Termo de busca. |
| `language` | string | `pt` | Aceito e normalizado para `pt` ou `en`, mas o controller não usa o valor. |

Resposta `200`: `{"total_documents": 3, "entries": [ ... ]}`, em ordem crescente de `position`.

O `search_term` casa com `tconst` **igual** ao termo, ou com `title` ou `director` que **contenham** o
termo, sem diferenciar maiúsculas.

| Código | Corpo |
|---|---|
| `200` | Com ou sem resultados. |
| `500` | `{"status": 500, "message": "Erro ao buscar recomendações"}` |

Um `page` ou `page_size` que não seja número inteiro na query string cai no valor padrão (é o
comportamento de `request.args.get(..., type=int)`).

### `POST /api/recommendations/add`

Query string:

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `language` | `pt` | Idioma repassado à pré-população. Não é normalizado nesta rota. |
| `prepopulate` | `true` | `false`, `0`, `no` ou vazio desligam a pré-população (sem diferenciar maiúsculas). Qualquer outro valor liga. |

Corpo (JSON): o documento do filme. Só `tconst` é obrigatório. O Swagger documenta `tconst`, `title`,
`original_title`, `year`, `director`, `genres`, `imdb_rating`, `runtime`, `position` e `url`, mas o
código grava o objeto exatamente como veio, com qualquer chave.

```bash
curl -X POST "http://localhost:5001/api/recommendations/add?prepopulate=false" \
  -H "Content-Type: application/json" \
  -d '{"tconst": "tt0053472", "title": "Breathless", "year": "1960", "director": "Jean-Luc Godard"}'
```

Resposta `201`, sem pré-população:

```json
{
  "data": "Filme adicionado com sucesso",
  "movie": {"tconst": "tt0053472", "title": "Breathless", "year": "1960", "director": "Jean-Luc Godard", "position": 4, "_id": "66f0..."}
}
```

Resposta `201`, com pré-população:

```json
{
  "data": "Filme adicionado e dados pré-populados com sucesso",
  "movie": { "...": "..." },
  "prepopulate": {"status": "success", "message": "Dados pré-populados com sucesso", "results": {"director": {}, "soundtrack": {}}}
}
```

| Código | Quando |
|---|---|
| `201` | Filme gravado. Vale também quando a pré-população falha. |
| `400` | Corpo vazio (`"Dados do filme são obrigatórios"`), corpo que não é objeto (`"Dados do filme inválidos"`), `tconst` ausente, vazio, só com espaços ou que não é string (`"tconst é obrigatório"`), ou `tconst` já cadastrado (`"Filme já existe na base de dados"`). |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | `{"error": "Erro ao adicionar filme: <texto da exceção>"}` |

### `POST /api/recommendations/bulk-add`

Mesma query string do `/add`. Corpo: uma lista JSON não vazia de filmes.

Resposta `201`:

```json
{
  "data": "2 filmes adicionados com sucesso",
  "movies": [ {"tconst": "tt1", "position": 4, "_id": "..."}, {"tconst": "tt2", "position": 5, "_id": "..."} ],
  "prepopulate_results": [
    {"tconst": "tt1", "title": null, "result": {"status": "success", "message": "...", "results": {}}}
  ],
  "skipped": 1
}
```

| Código | Quando |
|---|---|
| `201` | Pelo menos um filme novo foi gravado. |
| `400` | Corpo vazio ou que não é lista (`"Lista de filmes é obrigatória"`), ou nenhum filme novo para gravar (`"Todos os filmes já existem na base de dados"`). |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | `{"error": "Erro ao adicionar filmes: <texto da exceção>"}` |

### `DELETE /api/recommendations/<tconst>`

| Código | Corpo |
|---|---|
| `200` | `{"data": "Recommendation tt0053472 deleted"}` |
| `404` | `{"data": "Recommendation tt0053472 not found"}` |
| `500` | `{"data": "Failed to delete recommendation"}` |

### `DELETE /api/recommendations/clear`

Apaga todos os documentos da coleção. A docstring diz que serve para reimportar a lista.

| Código | Corpo |
|---|---|
| `200` | `{"data": "3 recommendations deleted"}` |
| `500` | `{"data": "Failed to clear recommendations"}` |

## Regras de negócio

### Posição na lista

- Se o filme chega sem `position`, recebe a maior posição numérica já gravada mais 1. Em coleção
  vazia, ou em que nenhum documento tem `position` numérica, recebe 1.
- Documentos sem `position`, ou com `position` que não é número, são ignorados nessa conta.
- Se o filme chega com `position`, o valor é mantido como veio. O código não confere se a posição já
  está em uso.
- No `bulk-add`, a numeração começa na próxima posição livre e avança de um em um apenas para os
  filmes que chegaram sem `position`.

### Duplicados

- No `/add`, `tconst` já cadastrado é `400`.
- No `bulk-add`, filmes já cadastrados são pulados, e um `tconst` repetido na mesma lista entra uma
  vez só (a primeira ocorrência).
- Itens da lista que não são objetos, ou sem `tconst` válido, são pulados.
- `skipped` é o tamanho da lista enviada menos a quantidade gravada. Ele soma os três casos:
  inválidos, já cadastrados e repetidos.

### Pré-população ao adicionar

- Com `prepopulate` ligado, o controller chama `prepopulate_movie_data` do módulo
  `movie_prepopulate` para cada filme gravado, na mesma requisição. A resposta só sai depois que as
  chamadas à OpenAI, ao Spotify e ao IMDB terminam.
- Se a pré-população lançar exceção, o filme continua gravado. No `/add`, a resposta é `201` com
  `"Filme adicionado com sucesso (pré-população falhou)"` e o texto do erro em `prepopulate_error`. No
  `bulk-add`, `prepopulate_results` vira `[{"error": "<texto>"}]`.
- Com `prepopulate` desligado, `prepopulate_results` vem como lista vazia.

## Casos de borda

- **A mensagem de sucesso não olha o resultado da pré-população.** `prepopulate_movie_data` devolve
  `status: "error"` sem lançar exceção quando não consegue gerar nada. Nesse caso o `/add` ainda
  responde `"Filme adicionado e dados pré-populados com sucesso"`. O resultado real está no campo
  `prepopulate`.
- **A mensagem do `400` do `bulk-add` é sempre "Todos os filmes já existem",** inclusive quando a
  lista só tinha itens inválidos.
- **O documento não passa por esquema.** Tipos e nomes de campos não são validados. O Swagger
  descreve `year`, `imdb_rating` e `runtime` como strings.
- **Não há índice único em `tconst` criado pelo código.** A checagem de duplicado é uma leitura
  seguida de uma escrita; duas requisições simultâneas podem gravar o mesmo `tconst`. Se existe índice
  único criado direto no banco é não verificado.
- **`page` menor que 1 em `/all`** não é recusado pela rota. O efeito em um MongoDB real é não
  verificado.
- **Remover uma recomendação não apaga** o diretor, a trilha nem o cache de detalhe ligados ao filme.
