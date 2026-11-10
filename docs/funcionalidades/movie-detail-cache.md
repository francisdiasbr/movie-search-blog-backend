# Detalhe do filme e cache (`movie_detail_cache`)

Arquivos: `movie_detail_cache/routes.py`, `movie_detail_cache/controller.py`. Prefixo:
`/api/movie-detail`. Coleção própria: `movie_detail_cache`. Lê também `recommendations`, `directors`
e `movie_soundtracks`. Usa os controllers de [diretores](directors.md) e [trilhas](music.md).

## O que faz

Junta em uma única resposta tudo o que a página de detalhe de um filme precisa: os dados do filme, o
diretor e a trilha sonora. O resultado montado fica guardado por 24 horas, por filme e por idioma.
Enquanto o cache vale, a página abre com uma leitura no banco, sem chamar OpenAI, Spotify ou IMDB.

O filme é procurado na coleção `recommendations`. Um filme que só existe em resenhas, posts ou
favoritos não tem detalhe por esta rota.

## Rotas

### `GET /api/movie-detail/<movie_id>`

| Parâmetro | Onde | Padrão | Descrição |
|---|---|---|---|
| `movie_id` | caminho | | `tconst` do filme, com igualdade exata. |
| `language` | query | `pt` | Idioma. Não é validado nem normalizado nesta rota. |

```bash
curl "http://localhost:5001/api/movie-detail/tt0053472?language=pt"
```

Resposta `200`, montada agora:

```json
{
  "cache_key": "tt0053472_pt",
  "movie_id": "tt0053472",
  "language": "pt",
  "movie": {"_id": "...", "tconst": "tt0053472", "title": "Breathless", "year": "1960", "director": "Jean-Luc Godard", "position": 1},
  "director": {"_id": "...", "name": "Jean-Luc Godard", "bio": "...", "photo": "..."},
  "soundtrack": {"_id": "...", "cache_key": "Breathless_1960", "tracks": [], "description": "...", "source": "gpt_spotify"},
  "created_at": "2026-11-10T18:42:07.123000",
  "from_cache": false,
  "_id": "66f0c0ffee0000000000abcd"
}
```

Resposta `200`, vinda do cache: os mesmos campos, com `from_cache: true` e mais
`cache_age_hours` (idade do cache em horas, com casas decimais).

| Código | Quando |
|---|---|
| `200` | Resposta montada ou lida do cache. Vale também quando diretor ou trilha vêm nulos. |
| `404` | Não há filme com esse `tconst` em `recommendations`: `{"error": "Filme não encontrado"}`. |
| `500` | Erro inesperado ou banco indisponível: `{"error": "Erro ao buscar cache de detalhes do filme"}` ou `{"error": "Erro ao criar cache de detalhes do filme"}`. |

### `POST /api/movie-detail/<movie_id>/invalidate`

Corpo opcional: `{"language": "pt"}`. Corpo ausente ou que não é objeto é tratado como `{}`.

- Com `language`, apaga o cache daquele filme naquele idioma.
- Sem `language`, apaga os caches do filme em todos os idiomas.

| Código | Corpo |
|---|---|
| `200` | `{"message": "Cache invalidado para filme tt0053472", "deleted_count": 1}`. Vale também quando não havia nada para apagar (`deleted_count: 0`). |
| `500` | `{"error": "Erro ao invalidar cache"}` |

### `POST /api/movie-detail/cleanup`

Apaga os caches com `created_at` anterior a 24 horas atrás.

| Código | Corpo |
|---|---|
| `200` | `{"message": "3 caches expirados removidos"}` |
| `500` | `{"error": "Erro ao limpar cache expirado"}` |

### `GET /api/movie-detail/stats`

Resposta `200`:

```json
{
  "total_caches": 10,
  "valid_caches": 7,
  "expired_caches": 3,
  "language_stats": [{"_id": "pt", "count": 8}, {"_id": "en", "count": 2}]
}
```

`valid_caches` conta os documentos com `created_at` nas últimas 24 horas. `expired_caches` é o total
menos os válidos. `language_stats` vem do mais usado para o menos usado. Em erro, responde `500` com
`{"error": "Erro ao buscar estatísticas do cache"}`.

## Passo a passo interno

### Leitura

1. Monta a chave `<movie_id>_<language>` e procura na coleção `movie_detail_cache`.
2. Se achou e `created_at` é uma data com menos de 24 horas, responde com o documento, acrescentando
   `from_cache: true` e `cache_age_hours`.
3. Se achou, mas o cache expirou ou `created_at` não é uma data, apaga todos os documentos com essa
   chave.
4. Monta um cache novo.

### Montagem

1. Procura o filme em `recommendations` por `tconst`. Sem filme, responde `404`.
2. Procura o diretor direto na coleção `directors`, pelo campo `director` do filme. Se achou e o
   idioma não é `pt`, traduz a biografia.
3. Procura a trilha direto na coleção `movie_soundtracks`, pela chave `<title>_<year>` (ou só
   `<title>`). Se achou e o idioma não é `pt`, traduz a descrição.
4. Se o diretor não estava gravado e o filme tem diretor, chama `get_director_info` do módulo
   `directors`, passando o `tconst` (o que habilita a busca da foto no IMDB).
5. Se a trilha não estava gravada, chama `get_movie_soundtrack` do módulo `music`.
6. Monta o documento com `cache_key`, `movie_id`, `language`, `movie`, `director`, `soundtrack`,
   `created_at` e `from_cache: false`.
7. Grava o documento, se ele estiver completo (veja a regra abaixo).
8. Responde `200`, tendo gravado ou não.

Os passos 2 e 3 existem para evitar o caminho mais lento quando os dados já foram gerados antes, por
exemplo pela [pré-população](prepopulate.md).

## Regras de negócio

### Validade de 24 horas

- O cache vale enquanto `agora - created_at` for menor que 24 horas.
- A expiração é verificada na leitura. O código não cria índice TTL; um cache expirado continua na
  coleção até alguém pedir aquele filme de novo ou chamar `/cleanup`.
- Cada idioma tem o seu documento. Montar o cache em `pt` não cria o de `en`.

### Quando o cache não é gravado

O documento só é gravado quando o diretor e a trilha são definitivos. A função `_is_final` considera
um dado **não** definitivo quando:

- ele é nulo ou vazio (a busca falhou);
- ele tem `placeholder: true` (biografia genérica do diretor);
- ele tem `source: "gpt"` (trilha sem dados do Spotify).

Há uma exceção: se o filme não tem o campo `director`, o diretor não é exigido.

Quando o cache não é gravado, a resposta sai normalmente com `from_cache: false` e sem `_id`, e a
próxima requisição refaz a montagem. O motivo está em um comentário do código: uma busca que falhou
não pode ficar congelada como nula por 24 horas.

Consequência: um filme para o qual a OpenAI nunca devolve faixas não chega a ter cache. Cada abertura
da página desse filme refaz as chamadas externas.

### O que fica dentro do cache

- Uma cópia do documento do filme, do diretor e da trilha, como estavam na hora da montagem. Mudanças
  posteriores nessas coleções só aparecem depois de 24 horas ou de um `invalidate`.
- No cache de idioma diferente de `pt`, a biografia e a descrição da trilha ficam guardadas já
  traduzidas. Esse é o único lugar em que uma tradução é persistida.

### Datas

- `created_at` é gravado com precisão de milissegundos, que é o que o MongoDB guarda. Assim, a
  primeira resposta e as respostas vindas do cache mostram o mesmo valor.
- Na resposta, `created_at` sai como texto ISO. A conversão é feita por `_json_safe`, que também
  converte qualquer `ObjectId` aninhado em string.

## Casos de borda

- **`language` livre.** Um valor como `es` cria a chave `<movie_id>_es`. Nesse caso, a tradução da
  biografia usa um prompt que pede inglês, e a da trilha pede o idioma informado. O conteúdo desse
  cache fica inconsistente. As rotas de `directors` e `music` normalizam o idioma; esta não.
- **Tradução que falha fica no cache.** Se a tradução falhar na montagem do cache em `en`, o texto em
  português é devolvido sem marca nenhuma, o documento é considerado definitivo e fica guardado por
  24 horas no cache de inglês.
- **Filme com vários diretores.** A busca direta em `directors` usa o texto inteiro (por exemplo
  `Joel Coen, Ethan Coen`) e não acha nada. A montagem cai em `get_director_info`, que resolve cada
  nome e devolve a resposta combinada.
- **Filme sem `title`.** A montagem falha e a resposta é `500`.
- **Diretor nulo na resposta.** Acontece quando o filme não tem diretor ou quando a busca do diretor
  devolveu erro.
- **`/cleanup` e `created_at` inválido.** O `cleanup` compara datas. Um documento com `created_at`
  que não é data não entra nessa comparação; ele é removido quando o filme for pedido de novo. Nas
  estatísticas, ele conta como expirado.
- **Montagens simultâneas.** Não há índice único em `cache_key` criado pelo código. Duas requisições
  ao mesmo tempo podem gravar dois documentos com a mesma chave. Na expiração, todos são apagados
  juntos.
- **Traduções próprias.** Este módulo tem as suas funções de tradução, com prompts mais curtos e
  tempo limite de 3 segundos, usadas só nos passos 2 e 3 da montagem. Quando a montagem passa por
  `get_director_info` ou `get_movie_soundtrack`, valem as traduções daqueles módulos.
