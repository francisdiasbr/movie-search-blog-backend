# Trilhas sonoras (`music`)

Arquivos: `music/routes.py`, `music/controller.py`. Prefixo: `/api/music`. Coleção:
`movie_soundtracks`. Serviços externos: OpenAI (lista de faixas, descrição e tradução) e Spotify
(dados de cada faixa).

## O que faz

Entrega a trilha sonora de um filme: uma descrição geral e uma lista de faixas com título, artista,
álbum, duração e links do Spotify. Na primeira consulta, a OpenAI indica as faixas e o Spotify
completa os dados de cada uma. O resultado é gravado e as consultas seguintes vêm do banco.

## Rotas

### `GET /api/music/soundtrack`

Query string:

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `title` | string | Sim | | Título do filme. |
| `year` | inteiro | Não | nenhum | Ano do filme. Um valor que não seja inteiro é ignorado. |
| `director` | string | Não | nenhum | Diretor. Só entra no prompt. |
| `language` | string | Não | `pt` | `pt` ou `en`. Qualquer outro valor vira `pt`. |

```bash
curl "http://localhost:5001/api/music/soundtrack?title=Breathless&year=1960&director=Jean-Luc%20Godard"
```

Resposta `200`:

```json
{
  "_id": "66f0c0ffee0000000000abcd",
  "movie_title": "Breathless",
  "movie_year": 1960,
  "movie_director": "Jean-Luc Godard",
  "tracks": [
    {
      "title": "New York Herald Tribune",
      "artist": "Martial Solal",
      "spotify_id": "4uLU6hMCjMI75M1A2tKUQC",
      "preview_url": null,
      "external_urls": {"spotify": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"},
      "album": {"name": "À bout de souffle", "images": [{"url": "https://i.scdn.co/image/..."}]},
      "duration_ms": 123000,
      "description": "Tema que acompanha a personagem pelas ruas de Paris."
    },
    {
      "title": "L'amour, la mort",
      "artist": "Martial Solal",
      "spotify_id": null,
      "preview_url": null,
      "external_urls": {},
      "album": null,
      "duration_ms": null,
      "description": ""
    }
  ],
  "description": "Jazz francês que marca o ritmo do filme.",
  "source": "gpt_spotify",
  "cache_key": "Breathless_1960"
}
```

| Código | Quando |
|---|---|
| `200` | Trilha encontrada no banco ou gerada agora. |
| `400` | `title` ausente ou vazio: `{"error": "Título do filme é obrigatório"}`. |
| `404` | Não havia trilha gravada e a OpenAI não devolveu faixas. Mensagem em `pt` (`"Não foi possível encontrar a trilha sonora do filme"`) ou em `en` (`"Could not find movie soundtrack"`). |
| `500` | Erro inesperado ou banco indisponível: `"Erro ao buscar trilha sonora"` ou `"Error searching soundtrack"`. |

### `GET /api/music/all`

| Código | Corpo |
|---|---|
| `200` | `{"soundtracks": [ ... ]}`, todos os documentos sem o campo `_id`. |
| `500` | `{"error": "Erro ao buscar trilhas sonoras"}` |

### `DELETE /api/music/soundtrack`

Query string: `title` (obrigatório) e `year` (opcional, inteiro).

| Código | Corpo |
|---|---|
| `200` | `{"message": "Trilha sonora de Breathless removida com sucesso"}` |
| `400` | `{"error": "Título do filme é obrigatório"}` |
| `404` | `{"message": "Trilha sonora de Breathless não encontrada"}` |
| `500` | `{"error": "Erro ao deletar trilha sonora"}` |

## Passo a passo interno

1. Calcula a `cache_key`: `<título>_<ano>` quando há ano, ou só `<título>`.
2. Procura na coleção `movie_soundtracks` por essa chave.
3. **Se achou:** se `language` não é `pt` e há descrição, traduz a descrição geral só para a
   resposta. Responde `200`.
4. **Se não achou,** pede as faixas à OpenAI:
   1. O prompt pede de 5 a 8 músicas, com nome, artista e uma descrição curta de cada uma, mais uma
      descrição geral, em formato JSON. O prompt é em português, ou em inglês quando `language=en`.
   2. O código procura um trecho entre `{` e `}` na resposta e tenta lê-lo como JSON.
   3. Se não há JSON válido, lê a resposta linha a linha (veja "Leitura manual" abaixo).
   4. Sem chave, com erro, ou sem nenhuma faixa no resultado, a rota responde `404`.
5. Busca cada faixa no Spotify:
   1. Faixa sem título é descartada.
   2. A consulta é `track:<título>` e, se houver artista, ` artist:<artista>`, com tipo `track` e
      limite de 1 resultado.
   3. Se o Spotify achou, a faixa leva os dados do Spotify. O título e o artista passam a ser os do
      Spotify (o primeiro artista da faixa), e a descrição continua sendo a da OpenAI.
   4. Se não achou, ou se a busca deu erro, a faixa entra com o título e o artista da OpenAI e os
      campos do Spotify vazios.
6. Decide a origem (`source`) e se grava (veja a regra abaixo).
7. Responde `200`.

### Leitura manual

Usada quando a resposta da OpenAI não tem JSON válido.

- Uma linha que começa com número seguido de `.` ou `)` é tratada como faixa, no formato
  `Título - Artista`. Linhas numeradas sem ` - ` são ignoradas.
- A primeira linha não vazia que não é numerada e não começa com `{` ou `}` vira a descrição geral.
- No máximo 8 faixas são mantidas.
- As faixas lidas assim não têm descrição individual.

## Regras de negócio

### `source` e quando a trilha é gravada

| `source` | Significado | Grava no banco |
|---|---|---|
| `gpt_spotify` | O Spotify foi consultado e respondeu a pelo menos uma busca. | Sim |
| `gpt` | O Spotify estava indisponível. As faixas vêm só da OpenAI, com todos os campos do Spotify vazios. | Não |

O Spotify é considerado indisponível quando falta `SPOTIFY_CLIENT_ID` ou `SPOTIFY_CLIENT_SECRET`,
quando a criação do cliente falha, ou quando **todas** as buscas lançam erro.

Uma resposta com `source: "gpt"`:

- não tem `_id`, porque nada foi gravado;
- será refeita na próxima consulta, com nova chamada à OpenAI e nova tentativa no Spotify;
- é tratada como provisória pelo [cache de detalhe](movie-detail-cache.md), que não grava o cache, e
  pela [pré-população](prepopulate.md), que não conta como sucesso.

Uma faixa não encontrada no Spotify não torna a trilha provisória. Se o Spotify respondeu, mesmo sem
achar nenhuma das faixas, a origem é `gpt_spotify` e a trilha é gravada com os campos do Spotify
vazios.

### `cache_key`

- A chave depende do título e do ano exatamente como chegaram. `Breathless` com ano e sem ano são
  duas trilhas diferentes. Títulos com grafia diferente também.
- O `DELETE` usa a mesma regra. Para apagar uma trilha gravada com ano, é preciso informar o ano.
- O diretor não entra na chave.

### Idioma

- A descrição geral é traduzida a cada requisição com `language=en`, sem gravar.
- As descrições individuais das faixas não são traduzidas.
- **A trilha é gravada no idioma da primeira requisição.** Se a primeira consulta a um filme usa
  `language=en`, o prompt é em inglês e os textos gravados ficam em inglês. Consultas posteriores em
  `pt` recebem esse texto em inglês, e consultas em `en` pedem a "tradução" de um texto que já está em
  inglês. O módulo `directors` não tem esse problema, porque sempre gera em português.

## Casos de borda

- **Faixas sem título.** São descartadas, sem afetar as outras. Se todas as faixas vierem sem título,
  nenhuma busca é feita no Spotify e a trilha é gravada com `tracks` vazio e `source: "gpt_spotify"`.
- **Tradução que falha** devolve a descrição original, sem aviso.
- **`movie_year` na resposta.** Vem como inteiro quando a trilha é gerada por esta rota. Quando a
  geração parte do detalhe do filme ou da pré-população, o ano vem do documento da recomendação, que
  pode ser string.
- **Trilha gravada tem `_id` na resposta de `/soundtrack`** e não tem em `/all`.
- **O modelo `Soundtrack` do Swagger** não lista `_id` nem `cache_key`, que fazem parte da resposta.
- **Não há índice único em `cache_key` criado pelo código.**

Os prompts, parâmetros e tempos limite estão em [integracoes.md](../integracoes.md).
