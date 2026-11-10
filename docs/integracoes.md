# Integrações externas

A API chama cinco sistemas externos: a API da OpenAI, a API do Spotify, o AWS S3, páginas do IMDB e
o MongoDB. Este documento descreve, para cada um, o que é chamado, com quais parâmetros, como a
chamada pode falhar e o que a API responde quando falha.

Uma regra vale para todas as integrações: as falhas são capturadas com `except Exception` e
convertidas em um valor de retorno. **O código não registra o erro em log.** Uma chave inválida, um
modelo recusado e um tempo limite estourado produzem o mesmo efeito visível, e a causa não fica
gravada em lugar nenhum.

## Resumo

| Serviço | Biblioteca | Quem chama | Para quê | Se falhar |
|---|---|---|---|---|
| OpenAI | `openai` 1.58.1 | `directors`, `music`, `movie_detail_cache` | Biografias, faixas e descrição de trilhas, traduções | Biografia genérica com `placeholder: true`; trilha `404`; tradução devolve o texto original |
| Spotify | `spotipy` 2.23.0 | `music` | Dados de cada faixa | Trilha devolvida com `source: "gpt"` e não gravada |
| S3 | `boto3` 1.40.23 | `images`, `home` | Listar imagens e ler legendas | `images`: `500` ou `404`; `home`: card com `imageUrl: null` |
| IMDB | `requests` 2.32.3 | `directors` | Foto do diretor | Diretor sem foto (`photo: null`) |
| MongoDB | `pymongo` | todos | Persistência | `500` |

## OpenAI

### O que a OpenAI faz neste projeto

São três usos, e só eles:

1. **Escrever a biografia de um diretor,** em português.
2. **Indicar as faixas da trilha sonora de um filme** e escrever uma descrição da trilha.
3. **Traduzir** a biografia e a descrição da trilha para a resposta em inglês.

O módulo `generate_blogpost` **não usa a OpenAI**. Apesar do nome, ele só lê posts já gravados na
coleção `blogposts`. Nenhum código deste repositório gera posts, resenhas ou opiniões com IA.

### Modelo

Todas as chamadas usam `client.chat.completions.create` com `model=OPENAI_MODEL`. O padrão é
`gpt-5.6-terra`, definido em `config.py`, com um comentário que explica a troca: o `gpt-3.5-turbo`
foi desligado em 23/10/2026.

**A troca de modelo ainda não foi validada com uma chamada real.** Os testes substituem o cliente da
OpenAI por um dublê; um único teste, o da geração de biografia, confere que o nome do modelo
configurado é repassado. Em particular:

- as chamadas enviam `max_tokens` e `temperature`, os mesmos parâmetros usados com o modelo anterior.
  Se o modelo novo aceita esses parâmetros é **não verificado**;
- se a OpenAI recusar a chamada, o efeito será silencioso: diretores com biografia genérica, trilhas
  respondendo `404` e traduções devolvendo o texto em português, sem nenhum registro do motivo.

### As seis chamadas

Um cliente `OpenAI(api_key=OPENAI_API_KEY)` é criado a cada chamada. Antes de criar o cliente, cada
função confere se `OPENAI_API_KEY` existe; sem chave, ela devolve o valor de falha sem tentar.

| # | Função | Uso | `max_tokens` | `temperature` | `timeout` | Valor em caso de falha |
|---|---|---|---|---|---|---|
| 1 | `directors.controller._generate_director_bio_with_ai` | Biografia | 300 | 0.7 | 5 s | `None` |
| 2 | `directors.controller._translate_director_bio` | Tradução da biografia | 400 | 0.3 | não definido | A biografia original |
| 3 | `music.controller._get_track_info_with_gpt` | Faixas e descrição | 500 | 0.7 | 5 s | `None` |
| 4 | `music.controller._translate_soundtrack_description` | Tradução da descrição | 150 | 0.3 | 3 s | A descrição original |
| 5 | `movie_detail_cache.controller._translate_director_bio` | Tradução da biografia | 400 | 0.3 | 3 s | A biografia original |
| 6 | `movie_detail_cache.controller._translate_soundtrack_description` | Tradução da descrição | 150 | 0.3 | 3 s | A descrição original |

A chamada 2 não passa `timeout`; vale o padrão da biblioteca `openai` (não verificado qual é). Se a
biblioteca refaz a chamada automaticamente depois de um erro, e quantas vezes, também é não
verificado; o código não configura isso.

### Prompts

**1. Biografia do diretor.** Mensagem de sistema: "Você é um especialista em cinema e escreve
biografias envolventes sobre diretores de cinema." A mensagem de usuário pede:

- uma biografia "rica e detalhada" do diretor, no estilo das biografias de artistas do Shazam;
- que inclua estilo cinematográfico, filmes mais importantes, técnicas marcantes, impacto na
  indústria, prêmios e reconhecimentos, influências e legado;
- entre 150 e 250 palavras, em português brasileiro, com tom respeitoso e informativo;
- honestidade quando não houver informação específica sobre o diretor, mantendo um tom positivo.

O prompt recebe apenas o nome do diretor. O filme e o `tconst` não entram. O texto devolvido é usado
sem os espaços das pontas; texto vazio é tratado como falha.

**2. Tradução da biografia (módulo `directors`).** Mensagem de sistema: "You are a professional
translator specializing in film and entertainment content." A mensagem de usuário pede a tradução
para o inglês, mantendo estilo, tom e nível de detalhe. O idioma de destino está escrito no prompt
como inglês; o parâmetro `language` só decide se a tradução acontece.

**3. Faixas da trilha.** Mensagem de sistema em português ("Você é um especialista em cinema e
música. Identifica trilhas sonoras icônicas de filmes.") ou em inglês, conforme `language`. A
mensagem de usuário traz o título do filme e, quando informados, o ano e o diretor, e pede:

- de 5 a 8 músicas mais importantes do filme;
- para cada uma, nome e artista ou compositor;
- uma descrição curta da importância da trilha;
- a resposta em JSON, com `tracks` (cada item com `title`, `artist` e `description`) e
  `description`.

A chamada não usa o modo de resposta em JSON da API; o formato é pedido só no texto do prompt. A
leitura da resposta está descrita em [funcionalidades/music.md](funcionalidades/music.md).

**4 e 6. Tradução da descrição da trilha.** Mensagem de usuário:
`Translate the following soundtrack description to <idioma>: <descrição>`. O idioma é o código
recebido (`en`). As mensagens de sistema diferem pouco entre os dois módulos.

**5. Tradução da biografia (módulo `movie_detail_cache`).** Versão curta da chamada 2:
`Translate the following film director biography to English. Maintain the same style and tone: <bio>`.

### Como falha e o que a API responde

| Situação | Biografia | Faixas da trilha | Traduções |
|---|---|---|---|
| Sem `OPENAI_API_KEY` | `200` com biografia genérica e `placeholder: true`; nada gravado | `404` | Texto original, `200` |
| Erro da API (chave inválida, modelo recusado, limite de uso) | Idem | `404` | Texto original, `200` |
| Tempo limite estourado | Idem | `404` | Texto original, `200` |
| Resposta com texto vazio | Idem | `404` | String vazia na resposta, `200` |
| Resposta sem JSON e sem linhas numeradas | não se aplica | `404` | não se aplica |

Consequências que vale conhecer:

- **Uma falha de tradução é invisível para quem chama.** A resposta sai `200`, com o texto em
  português no lugar do inglês, e sem campo que avise.
- **Uma falha de geração não é gravada.** A biografia genérica e a trilha `404` não deixam nada no
  banco, e a próxima requisição tenta de novo.
- **Não é possível distinguir "o filme não tem trilha conhecida" de "a OpenAI falhou".** Os dois
  casos respondem `404` com a mesma mensagem.
- **Limite de 300 tokens na biografia.** O prompt pede até 250 palavras e a chamada limita a resposta
  a 300 tokens. Se esse limite corta biografias no meio é não verificado.

## Spotify

Usado só em `music.controller._search_tracks_on_spotify`.

| Item | Valor |
|---|---|
| Autenticação | Fluxo client credentials (`SpotifyClientCredentials`), com `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`. Não há login de usuário. |
| Chamada | `sp.search(q=..., type="track", limit=1)`, uma por faixa, em sequência. |
| Consulta | `track:<título>`, mais ` artist:<artista>` quando a OpenAI informou o artista. |
| Dados aproveitados | `name`, nome do primeiro artista, `id`, `preview_url`, `external_urls`, nome e imagens do álbum, `duration_ms`. |
| Tempo limite | Não definido no código; vale o padrão do `spotipy` (não verificado). |

Um cliente novo é criado a cada trilha gerada. O token de acesso não é guardado pelo código entre
requisições; se o `spotipy` guarda por conta própria é não verificado.

### Como falha

| Situação | Efeito | Resposta da API |
|---|---|---|
| Falta `SPOTIFY_CLIENT_ID` ou `SPOTIFY_CLIENT_SECRET` | Spotify indisponível | `200`, `source: "gpt"`, nada gravado |
| Falha ao criar o cliente | Spotify indisponível | Idem |
| Todas as buscas lançam erro (por exemplo, credenciais recusadas) | Spotify indisponível | Idem |
| Algumas buscas lançam erro | As faixas com erro entram sem dados do Spotify | `200`, `source: "gpt_spotify"`, gravado |
| A busca não acha a faixa | A faixa entra sem dados do Spotify | `200`, `source: "gpt_spotify"`, gravado |

Quando o Spotify está indisponível, as faixas da OpenAI são devolvidas com `spotify_id`,
`preview_url`, `album` e `duration_ms` nulos e `external_urls` vazio. A trilha não é gravada para que
a próxima consulta tente de novo com o Spotify.

A busca pega o primeiro resultado do Spotify, sem conferir se o título e o artista batem com o que
foi pedido. Uma faixa homônima de outro artista pode ser aceita.

## AWS S3

Dois módulos usam o S3, cada um com o seu cliente `boto3`, criado uma vez por processo com
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e região `us-east-2`.

| Módulo | Operação | Para quê |
|---|---|---|
| `images` | `list_objects_v2(Bucket, Prefix="<tconst>/")` | Listar as imagens de um filme. |
| `images` | `get_object_tagging(Bucket, Key)` | Ler as legendas (`subtitle_pt`, `subtitle_en`). Uma chamada por imagem. |
| `home` | `list_objects_v2(Bucket, Prefix="<tconst>/", MaxKeys=1)` | Achar uma imagem para o card. Uma chamada por resenha da página, em até 5 threads. |

As URLs são montadas por concatenação, sem assinatura. A API nunca baixa o conteúdo das imagens.

### Como falha

| Módulo e rota | Situação | Resposta |
|---|---|---|
| `GET /api/images/<tconst>` | Qualquer exceção (credenciais, rede, permissão, erro em uma das tags) | `500`, `{"status": 500, "message": "Erro ao listar imagens"}` |
| `GET /api/images/<tconst>/<filename>` | `ClientError` com código `NoSuchKey`, `NotFound` ou `404` | `404`, `"Imagem não encontrada"` |
| `GET /api/images/<tconst>/<filename>` | Qualquer outra falha | `500`, `"Erro ao buscar imagem"` |
| `POST /api/home/cards` | Qualquer exceção na busca da imagem de uma resenha | `200`; aquele card sai com `imageUrl: null` |

O `home` foi escrito para que o S3 fora do ar não impeça a página inicial de carregar: os cards saem
sem imagem. No `images`, a falha é devolvida a quem chamou.

## IMDB

Não é uma API. O módulo `directors` baixa duas páginas HTML públicas do IMDB e extrai dados com
expressões regulares.

| Passo | URL | O que procura |
|---|---|---|
| 1 | `https://www.imdb.com/title/<tconst>/` | Um link `/name/nm<dígitos>/` cujo texto é o nome do diretor. |
| 2 | `https://www.imdb.com/name/<id>/` | A primeira URL de imagem em `m.media-amazon.com/images/M/`. |

As duas requisições usam `requests.get` com um `User-Agent` de navegador e `timeout=3`.

### Como falha

Qualquer falha (rede, tempo limite, status de erro, nome não encontrado no HTML, página sem imagem)
resulta em `None`, e o diretor fica com `photo: null`. A rota de diretor não muda de status por causa
disso.

Esta integração depende da estrutura do HTML do IMDB e de o site aceitar a requisição. Se ela
funciona hoje contra o site real é **não verificado**: os testes usam páginas HTML de exemplo. Se o
IMDB mudar o HTML ou bloquear a requisição, o efeito é silencioso: os diretores passam a ficar sem
foto.

A URL da foto aponta para o servidor de imagens do IMDB. A API guarda só a URL, não a imagem.

## MongoDB

| Item | Valor |
|---|---|
| Biblioteca | `pymongo` |
| Conexão | `MONGODB_CONNECTION_STRING`; o `.env.example` mostra o formato `mongodb+srv://` do Atlas |
| Banco | `MONGODB_DATABASE` |
| Cliente | Um por processo, criado na primeira requisição que precisa do banco |
| Teste de conexão | `client.server_info()` na criação |

Há uma alteração local, ainda não commitada, em `requirements.txt`: a linha do `pymongo` passou de
`pymongo==4.10.1` para `pymongo>=4.14.5`. A versão efetivamente instalada depende do ambiente.

### Como falha

- Se a conexão falha, `get_mongo_client` devolve `None`, nada é guardado, e a próxima requisição
  tenta conectar de novo. Cada tentativa espera o tempo limite padrão do `pymongo` (não verificado).
- Com o banco indisponível, todas as rotas que usam o banco respondem `500`. As mensagens variam por
  módulo; veja a convenção de erros em [arquitetura.md](arquitetura.md).
- A rota `GET /` e o Swagger em `/docs` não usam o banco e continuam respondendo.
- Uma falha no meio de uma operação é capturada pelo `except` do controller e também vira `500`.

## O que não existe

Para evitar suposições, estes pontos foram conferidos no código:

- Não há fila, tarefa em segundo plano nem agendador. Toda chamada externa acontece dentro da
  requisição HTTP que a disparou.
- Não há nova tentativa, controle de taxa nem disjuntor escritos no código.
- Não há cache em memória. O único cache é a coleção `movie_detail_cache`.
- Não há chamada a TMDB, OMDb ou outra base de filmes. O docstring de `tests/conftest.py` cita TMDB,
  mas nenhum código do repositório o chama.
- Não há envio de arquivos ao S3.
