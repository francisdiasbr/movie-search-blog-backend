# Opiniões pessoais (`personal_opinion`)

Arquivos: `personal_opinion/routes.py`, `personal_opinion/controller.py`. Prefixo:
`/api/personal-opinion`. Coleção: `personal_opinions`.

## O que faz

Guarda a opinião pessoal da autora sobre cada filme: um texto principal (`opinion`) e dois campos
complementares (`enjoying_1` e `enjoying_2`). A API lista, busca, lê e atualiza opiniões. Não há rota
para criar nem para apagar; a criação acontece fora deste repositório (não verificado).

## Rotas

As duas primeiras rotas ficam em `/api/personal-opinion/`, com barra no final. Sem a barra, o Flask
responde `308` redirecionando para o caminho com barra.

### `GET /api/personal-opinion/`

Devolve todas as opiniões, sem paginação.

| Código | Corpo |
|---|---|
| `200` | `{"data": [ ...documentos... ]}`. Coleção vazia devolve `{"data": []}`. |
| `500` | `{"status": 500, "message": "Erro ao recuperar opiniões pessoais"}` |

### `POST /api/personal-opinion/`

Busca com filtros e paginação. Corpo (JSON, objeto obrigatório):

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtros. `null` equivale a nenhum filtro. |
| `page` | inteiro | `1` | Página. |
| `page_size` | inteiro | `10` | Itens por página. |

| Código | Corpo |
|---|---|
| `200` | `{"total_documents": 1, "entries": [ ... ]}`, com ou sem resultados. |
| `400` | Corpo que não é objeto: `{"status": 400, "message": "Dados de entrada inválidos"}` |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | `{"status": 500, "message": "Erro ao pesquisar opiniões pessoais"}` |

Campos de texto (trecho, sem diferenciar maiúsculas): `tconst`, `opinion`, `enjoying_1`,
`enjoying_2`. Os demais filtros são igualdade exata.

### `GET /api/personal-opinion/<tconst>`

| Código | Corpo |
|---|---|
| `200` | `{"data": {"_id": "...", "tconst": "tt0053472", "opinion": "...", "enjoying_1": "...", "enjoying_2": "..."}}` |
| `404` | `{"status": 404, "message": "Opinião não encontrada"}` |
| `500` | `{"status": 500, "message": "Erro ao recuperar opinião pessoal"}` |

### `PUT /api/personal-opinion/<tconst>`

Atualiza uma opinião que já existe. Corpo (JSON, objeto):

| Campo | Tipo | Descrição |
|---|---|---|
| `opinion` | string | Texto da opinião. |
| `enjoying_1` | string | Campo complementar. |
| `enjoying_2` | string | Campo complementar. |

Basta enviar um dos três. Exemplo:

```bash
curl -X PUT http://localhost:5001/api/personal-opinion/tt0053472 \
  -H "Content-Type: application/json" \
  -d '{"opinion": "Revi e gostei ainda mais."}'
```

| Código | Corpo |
|---|---|
| `200` | `{"status": 200, "message": "Opinião atualizada com sucesso"}` |
| `400` | Corpo que não é objeto (`"Dados de entrada inválidos"`) ou sem nenhum dos três campos (`"Nenhum campo válido para atualizar"`). |
| `404` | `{"status": 404, "message": "Opinião não encontrada"}` |
| `500` | `{"status": 500, "message": "Erro ao atualizar opinião pessoal"}` |

## Regras e casos de borda

- **Só três campos são graváveis.** Qualquer outra chave do corpo é ignorada. Não dá para trocar o
  `tconst` de uma opinião por esta rota.
- **A ordem das verificações no `PUT`** é: existe a opinião (`404`), depois há campo válido (`400`).
- **Reenviar os mesmos valores é `200`.** O código não olha quantos documentos foram modificados.
- **O Swagger marca os três campos como obrigatórios,** mas o código aceita qualquer subconjunto. Os
  tipos dos valores não são validados.
- **Mais de uma opinião para o mesmo `tconst`:** o `GET` devolve a primeira encontrada e o `PUT`
  atualiza uma só (`update_one`).
- **`page` e `page_size` não são validados.**
