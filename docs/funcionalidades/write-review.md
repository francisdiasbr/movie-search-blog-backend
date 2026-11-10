# Resenhas autorais (`write_review`)

Arquivos: `write_review/routes.py`, `write_review/controller.py`. Prefixo: `/api/write-review`.
Coleção: `authoralreviewslist`.

## O que faz

Entrega as resenhas escritas pela autora do blog. O módulo só lê: não há rota para criar, editar ou
apagar resenhas. Quem grava na coleção não está neste repositório (não verificado).

## Rotas

### `POST /api/write-review/search`

Corpo (JSON):

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `filters` | objeto | `{}` | Filtros. `null` equivale a nenhum filtro. |
| `page` | inteiro | `1` | Página. |
| `page_size` | inteiro | `10` | Itens por página. |

Resposta `200`:

```json
{
  "total_documents": 2,
  "entries": [
    {
      "_id": "66f0c0ffee0000000000abcd",
      "tconst": "tt0053472",
      "primaryTitle": "Breathless",
      "content": {"pt": {"text": "..."}, "en": {"text": "..."}}
    }
  ]
}
```

Cada item de `entries` é o documento inteiro da coleção, com `_id` em string.

| Código | Quando |
|---|---|
| `200` | Consulta feita, com ou sem resultados. |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | Erro na consulta ou banco indisponível: `{"status": 500, "message": "Erro ao pesquisar opiniões pessoais"}`. |

### `GET /api/write-review/<tconst>`

Resposta `200`: `{"data": { ...documento da resenha... }}`.

| Código | Quando |
|---|---|
| `200` | Resenha encontrada. |
| `404` | Não há resenha com esse `tconst`: `{"status": 404, "message": "Opinião não encontrada"}`. |
| `500` | Erro na consulta: `{"status": 500, "message": "Erro ao recuperar opinião pessoal"}`. |

## Regras de filtro

| Filtro | Comportamento |
|---|---|
| `tconst`, `primaryTitle` (string) | Trecho, sem diferenciar maiúsculas. |
| `content` (string) | Procura o trecho em `content.pt.text`, em `content.en.text` e em `content` (para documentos em que `content` é texto simples). Vira um `$or`. |
| Qualquer outro | Igualdade exata, repassado ao MongoDB. |

O filtro `content` combina com os outros por "e".

## Casos de borda

- **Mensagens de erro falam em "opinião".** Os textos foram herdados do módulo `personal_opinion`. O
  sentido é "resenha".
- **Se houver mais de uma resenha para o mesmo `tconst`,** a rota devolve a primeira que o MongoDB
  encontrar.
- **`GET /api/write-review/search`** cai na rota de `tconst` e responde `404`, porque `search` é
  tratado como identificador. A busca é só por `POST`.
- **Corpo que não é objeto** (uma lista, por exemplo) não é validado e causa `500` genérico do
  flask-restx. Corpo JSON `null` é tratado como `{}`.
- **`page` e `page_size` não são validados.**
- **Função sem rota.** `get_all_write_reviews` existe no controller e é testada, mas nenhuma rota a
  chama.
- **O modelo `ReviewOutput` do Swagger** descreve `content.pt.text`, `content.en.text`, `created_at`,
  `isAiGenerated`, `references` e `images`. Ele documenta a forma esperada; a rota devolve o que
  estiver no banco, sem filtrar.
