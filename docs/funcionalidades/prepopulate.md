# Pré-população (`movie_prepopulate`)

Arquivos: `movie_prepopulate/routes.py`, `movie_prepopulate/controller.py`. Prefixo:
`/api/prepopulate`. Não tem coleção própria: lê `recommendations` e, por meio dos controllers de
[diretores](directors.md) e [trilhas](music.md), grava em `directors` e `movie_soundtracks`.

Script relacionado: `process_all_movies.py`, na raiz do repositório.

## O que faz

Gera com antecedência o diretor e a trilha sonora de um filme, para que a primeira abertura da página
de detalhe não precise esperar OpenAI, Spotify e IMDB. Pode rodar para um filme ou para a lista
inteira de recomendações, e informa quanto da lista já está coberto.

A pré-população não grava o cache de detalhe. Ela deixa prontos os dados que o
[cache de detalhe](movie-detail-cache.md) vai ler.

## Rotas

Em todas as rotas de execução, o corpo da resposta é o objeto de resultado, e o código HTTP é
derivado do campo `status` desse objeto.

### `POST /api/prepopulate/<movie_id>`

Pré-popula um filme já cadastrado em `recommendations`, localizado por `tconst`.

Corpo opcional: `{"language": "pt"}`. Corpo ausente ou que não é objeto é tratado como `{}`.

| `status` no corpo | Código | Significado |
|---|---|---|
| `success` | `200` | Pelo menos um dos dois (diretor, trilha) foi gerado e gravado agora. |
| `already_exists` | `200` | Diretor e trilha já estavam gravados. Nada foi chamado. |
| `not_found` | `404` | Não há filme com esse `tconst`. |
| `error` | `500` | Nada foi gravado, ou houve exceção. |

Exemplo de `success`:

```json
{
  "status": "success",
  "message": "Dados pré-populados com sucesso",
  "results": {
    "director": {"_id": "...", "name": "Jean-Luc Godard", "bio": "...", "photo": null},
    "soundtrack": {"_id": "...", "movie_title": "Breathless", "tracks": [], "source": "gpt_spotify", "cache_key": "Breathless_1960"}
  }
}
```

Exemplo de `error`:

```json
{"status": "error", "message": "Não foi possível pré-popular os dados", "results": {}}
```

### `POST /api/prepopulate/movie`

Pré-popula um filme cujos dados vêm no corpo, sem consultar `recommendations`. A docstring diz que é
usada ao inserir um filme novo.

Corpo (JSON):

| Campo | Obrigatório | Descrição |
|---|---|---|
| `title` | Sim, se a trilha ainda não existe | Título do filme. |
| `year` | Não | Ano. Entra na chave da trilha. |
| `director` | Não | Nome do diretor, ou nomes separados por vírgula. |
| `tconst` | Não | Usado para buscar a foto do diretor no IMDB. |
| `language` | Não | Idioma, padrão `pt`. Vai no mesmo objeto dos dados do filme. |

| Código | Quando |
|---|---|
| `200` | `status` igual a `success` ou `already_exists`. |
| `400` | Corpo vazio: `{"error": "Dados do filme são obrigatórios"}`. |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | `status` igual a `error`. |

### `POST /api/prepopulate/all`

Pré-popula todos os filmes de `recommendations`.

Corpo (JSON; o cabeçalho `Content-Type: application/json` é exigido, mesmo com corpo `{}`):

| Campo | Padrão | Descrição |
|---|---|---|
| `language` | `pt` | Idioma repassado a cada filme. |
| `max_workers` | `3` | Quantos filmes são processados ao mesmo tempo. |

Resposta `200`:

```json
{
  "status": "completed",
  "total_movies": 40,
  "success_count": 5,
  "already_exists_count": 33,
  "error_count": 2,
  "results": [
    {"status": "already_exists", "message": "Dados já existem"},
    {"status": "success", "message": "Dados pré-populados com sucesso", "results": {}}
  ]
}
```

| Código | Quando |
|---|---|
| `200` | A execução terminou (`status: "completed"`), mesmo que alguns filmes tenham dado erro. |
| `415` | Requisição sem `Content-Type: application/json`. |
| `500` | Erro geral: `{"status": "error", "message": "Erro geral: <texto>"}`. Exemplos: banco indisponível, `max_workers` igual a zero. |

### `GET /api/prepopulate/stats`

Resposta `200`:

```json
{
  "total_movies": 40,
  "total_directors": 31,
  "total_soundtracks": 36,
  "director_coverage": 95.0,
  "soundtrack_coverage": 90.0,
  "overall_coverage": 92.5
}
```

Em erro, responde `500` com `{"error": "Erro ao buscar estatísticas: <texto>"}`.

## Passo a passo interno

### Um filme (`prepopulate_movie_data`)

1. Verifica se o diretor já existe: procura em `directors` um documento com `name` igual ao campo
   `director` do filme. Filme sem diretor é tratado como "diretor resolvido".
2. Verifica se a trilha já existe: procura em `movie_soundtracks` a chave `<title>_<year>` (ou só
   `<title>`).
3. Se os dois existem, devolve `already_exists`.
4. Se falta o diretor, chama `get_director_info` com o nome, o `tconst` e o idioma. O resultado só é
   aceito se o código for `200` e a resposta não tiver `placeholder`.
5. Se falta a trilha, chama `get_movie_soundtrack`. O resultado só é aceito se o código for `200` e
   `source` for diferente de `gpt`.
6. Se nada foi aceito, devolve `error`. Se pelo menos um foi aceito, devolve `success` com o que foi
   aceito em `results`.

Diretor e trilha de um mesmo filme são buscados um depois do outro.

### Todos os filmes (`prepopulate_all_movies`)

1. Lê todos os documentos de `recommendations`.
2. Envia cada filme para um `ThreadPoolExecutor` com `max_workers` threads. O paralelismo é entre
   filmes.
3. Recolhe os resultados na ordem em que terminam.
4. Conta quantos resultados têm cada `status`.

A requisição HTTP fica aberta até o último filme terminar. Não há fila nem execução em segundo plano.

## Regras de negócio

### O que conta como pré-populado

Só conta o que foi gravado. Biografia genérica (`placeholder: true`) e trilha sem Spotify
(`source: "gpt"`) são respostas válidas das rotas de diretor e de trilha, mas não são gravadas por
elas, então a pré-população as descarta. Um filme nessas condições devolve `error` e será tentado de
novo na próxima execução.

`success` significa "pelo menos metade deu certo". Se o diretor foi gravado e a trilha falhou, o
resultado é `success` com só `director` em `results`.

### Cálculo de cobertura

A cobertura é medida por filme, sobre o total de filmes em `recommendations`.

- **Diretor.** Um filme está coberto quando **todos** os nomes do seu campo `director` (separados por
  vírgula) existem em `directors`. Filme sem diretor conta como coberto.
- **Trilha.** Um filme está coberto quando a chave `<title>_<year>` (ou só `<title>`, se não há ano)
  existe em `movie_soundtracks`. Uma trilha gravada sem o ano não cobre um filme que tem ano.
- `director_coverage` e `soundtrack_coverage` são percentuais com uma casa decimal.
- `overall_coverage` é a média simples dos dois percentuais (antes do arredondamento), com uma casa
  decimal.
- Sem filmes, as três coberturas são `0`.
- `total_directors` e `total_soundtracks` são a contagem bruta das coleções. Eles podem ser maiores
  que `total_movies`, porque as coleções guardam também diretores e trilhas de filmes que não estão
  nas recomendações. A cobertura nunca passa de 100%.

Exemplo, tirado de `tests/test_movie_prepopulate_controller.py`: três filmes, dois deles com todos os
diretores gravados e um com a trilha gravada. `director_coverage` é `66.7`, `soundtrack_coverage` é
`33.3` e `overall_coverage` é `50.0`.

## Casos de borda

- **Filme com vários diretores nunca é `already_exists`.** A verificação do passo 1 procura o texto
  inteiro (`Joel Coen, Ethan Coen`) como um único nome, e os diretores são gravados um a um. Para
  esses filmes, `get_director_info` é chamado em toda execução e o resultado combinado é aceito, de
  modo que o filme aparece como `success` repetidamente. O cálculo de cobertura trata o caso certo,
  separando os nomes.
- **Os resultados de `/all` não identificam o filme.** Cada item de `results` traz `status` e
  `message`, sem `tconst` nem título, e a ordem é a de término. Dá para saber quantos falharam, mas
  não quais.
- **Filme sem `title`** resulta em `error` com a mensagem `Erro: 'title'`.
- **`max_workers` igual a zero** resulta em `500` com a mensagem do `ThreadPoolExecutor`.
- **Corpo em formato de lista** em `/all` ou `/movie` não é tratado e causa `500` genérico do
  flask-restx.
- **`language` não é normalizado.** O valor é repassado como veio a `get_director_info` e
  `get_movie_soundtrack`.
- **Idioma da trilha.** Pré-popular com `language: "en"` grava a trilha com textos em inglês. Veja a
  seção de idioma em [music.md](music.md).
- **Custo e limites.** `/all` com muitos filmes faltando dispara, por filme, até duas chamadas de
  chat à OpenAI, uma busca no Spotify por faixa e até duas requisições ao IMDB por diretor. O código não tem controle
  de taxa nem nova tentativa.

## Script `process_all_movies.py`

Script avulso que usa a API por HTTP, em `http://localhost:5001/api`. Precisa do servidor rodando
localmente.

1. Lê `/prepopulate/stats` e imprime os totais.
2. Chama `/prepopulate/all` com `{"language": "pt", "max_workers": 3}` e imprime as contagens.
3. Lê `/prepopulate/stats` de novo e imprime quantos diretores e trilhas foram acrescentados.
4. Invalida o cache de detalhe do filme `tt0060304` em `pt`, pede o detalhe e imprime o tempo da
   requisição.

O script não faz parte da suíte de testes.
