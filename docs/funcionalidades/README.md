# Funcionalidades

Um documento por módulo. Todos seguem a mesma ordem: o que a feature faz para quem usa, as rotas, o
passo a passo interno, as regras de negócio e os casos de borda.

Os exemplos usam `http://localhost:5001`, porque a API não está publicada. Os valores dos exemplos
são ilustrativos; a forma das respostas é a que o código monta.

`tconst` é o identificador de um título no IMDB, como `tt0053472`.

## Todas as rotas

| Método | Caminho | Módulo | O que faz |
|---|---|---|---|
| `GET` | `/` | `app.py` | Status da API. |
| `GET` | `/docs` | flask-restx | Swagger UI. A especificação fica em `/swagger.json`. |
| `POST` | `/api/home/cards` | [home](home.md) | Cards da página inicial, com a primeira imagem de cada resenha. |
| `POST` | `/api/write-review/search` | [write_review](write-review.md) | Busca resenhas. |
| `GET` | `/api/write-review/<tconst>` | [write_review](write-review.md) | Resenha de um filme. |
| `POST` | `/api/generate-blogpost/search` | [generate_blogpost](generate-blogpost.md) | Busca posts. |
| `GET` | `/api/generate-blogpost/<tconst>` | [generate_blogpost](generate-blogpost.md) | Post de um filme. |
| `GET` | `/api/personal-opinion/` | [personal_opinion](personal-opinion.md) | Todas as opiniões. |
| `POST` | `/api/personal-opinion/` | [personal_opinion](personal-opinion.md) | Busca opiniões. |
| `GET` | `/api/personal-opinion/<tconst>` | [personal_opinion](personal-opinion.md) | Opinião sobre um filme. |
| `PUT` | `/api/personal-opinion/<tconst>` | [personal_opinion](personal-opinion.md) | Atualiza a opinião sobre um filme. |
| `POST` | `/api/favorites/search` | [favorites](favorites.md) | Busca filmes favoritados. |
| `GET` | `/api/recommendations/random` | [recommendations](recommendations.md) | Todas as recomendações, por `position`. |
| `GET` | `/api/recommendations/all` | [recommendations](recommendations.md) | Recomendações com paginação e busca. |
| `POST` | `/api/recommendations/add` | [recommendations](recommendations.md) | Adiciona uma recomendação. |
| `POST` | `/api/recommendations/bulk-add` | [recommendations](recommendations.md) | Adiciona várias. |
| `DELETE` | `/api/recommendations/<tconst>` | [recommendations](recommendations.md) | Remove uma. |
| `DELETE` | `/api/recommendations/clear` | [recommendations](recommendations.md) | Remove todas. |
| `GET` | `/api/directors/all` | [directors](directors.md) | Diretores gravados. |
| `GET` | `/api/directors/<nome>` | [directors](directors.md) | Diretor, gerando a biografia se preciso. |
| `DELETE` | `/api/directors/<nome>` | [directors](directors.md) | Remove um diretor. |
| `GET` | `/api/music/all` | [music](music.md) | Trilhas gravadas. |
| `GET` | `/api/music/soundtrack` | [music](music.md) | Trilha de um filme, gerando se preciso. |
| `DELETE` | `/api/music/soundtrack` | [music](music.md) | Remove a trilha de um filme. |
| `GET` | `/api/images/<tconst>` | [images](images.md) | Imagens de um filme. |
| `GET` | `/api/images/<tconst>/<filename>` | [images](images.md) | Uma imagem. |
| `GET` | `/api/movie-detail/<movie_id>` | [movie_detail_cache](movie-detail-cache.md) | Filme, diretor e trilha em uma resposta, com cache. |
| `POST` | `/api/movie-detail/<movie_id>/invalidate` | [movie_detail_cache](movie-detail-cache.md) | Apaga o cache de um filme. |
| `POST` | `/api/movie-detail/cleanup` | [movie_detail_cache](movie-detail-cache.md) | Apaga os caches expirados. |
| `GET` | `/api/movie-detail/stats` | [movie_detail_cache](movie-detail-cache.md) | Estatísticas do cache. |
| `POST` | `/api/prepopulate/all` | [movie_prepopulate](prepopulate.md) | Pré-popula todos os filmes. |
| `POST` | `/api/prepopulate/movie` | [movie_prepopulate](prepopulate.md) | Pré-popula um filme enviado no corpo. |
| `POST` | `/api/prepopulate/<movie_id>` | [movie_prepopulate](prepopulate.md) | Pré-popula um filme já cadastrado. |
| `GET` | `/api/prepopulate/stats` | [movie_prepopulate](prepopulate.md) | Cobertura da pré-população. |

Onde uma rota fixa e uma rota com parâmetro disputam o mesmo caminho (por exemplo
`/api/directors/all` e `/api/directors/<nome>`), a rota fixa ganha. Esse é o comportamento do
roteador do Flask e é exercitado nos testes de `tests/test_app.py`.

## Rota de status

`GET /` responde `200` com:

```json
{
  "status": "online",
  "message": "Movie Search Blog API is running",
  "docs": "/docs",
  "version": "1.0"
}
```

O valor `online` é fixo no código. A rota não consulta o banco nem os serviços externos.

## Padrões que se repetem

- **Busca paginada.** `home`, `write_review`, `generate_blogpost`, `personal_opinion` e `favorites`
  recebem `filters`, `page` e `page_size` no corpo de um `POST`, ordenam por `_id` decrescente (os
  mais novos primeiro) e devolvem `total_documents` e `entries`.
- **Filtros.** Cada módulo tem uma lista de campos de texto. Um filtro em campo de texto, com valor
  do tipo string, vira busca por trecho sem diferenciar maiúsculas (`$regex` com opção `i`). Qualquer
  outro filtro é repassado ao MongoDB como veio, com igualdade exata. O valor do filtro de texto é
  usado como expressão regular, sem escape.
- **Idioma.** `directors` e `music` aceitam `language` igual a `pt` ou `en`; qualquer outro valor
  vira `pt`. `movie_detail_cache` e `movie_prepopulate` não fazem essa normalização.
- **Geração sob demanda.** `directors` e `music` procuram primeiro no banco. Só chamam serviços
  externos quando o dado não existe, e só gravam o resultado quando ele é definitivo.
