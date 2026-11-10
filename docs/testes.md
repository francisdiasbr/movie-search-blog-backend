# Testes

A suíte roda inteira offline. Na última execução local feita para esta documentação, foram 326 testes
aprovados em 0,36 segundo.

## Como rodar

```bash
pip install -r requirements-dev.txt   # instala também o requirements.txt
python -m pytest                      # a suíte inteira
python -m pytest tests/test_music_controller.py          # um arquivo
python -m pytest -k "placeholder"                         # por trecho do nome
python -m black --check .                                 # formatação, como no CI
```

Não é preciso ter `.env`, banco, chaves nem acesso à rede. Se existir um `.env` com credenciais
reais, ele não é usado: veja "Credenciais falsas" abaixo.

Configuração do pytest (`pytest.ini`): os testes ficam em `tests/` e a raiz do repositório entra no
caminho de importação (`pythonpath = .`), o que permite `import config` e `from app import app`.

Dependências de desenvolvimento (`requirements-dev.txt`): `pytest` 9.2.0, `mongomock` 4.3.0 e `black`
24.10.0.

## Organização

Há um arquivo de teste por controller, mais um arquivo para o app completo.

| Arquivo | Funções de teste | O que cobre |
|---|---|---|
| `tests/conftest.py` | | Fixtures compartilhadas e guardas contra chamadas externas. |
| `tests/test_app.py` | 54 | O app Flask de ponta a ponta pelo cliente de teste: roteamento, leitura de query string e corpo, códigos de status, Swagger e CORS. |
| `tests/test_directors_controller.py` | 29 | Diretor gravado, geração, tradução, foto do IMDB, `placeholder`, vários diretores, remoção. |
| `tests/test_music_controller.py` | 29 | Trilha gravada, geração com OpenAI e Spotify, `source`, leitura manual da resposta, tradução, remoção. |
| `tests/test_movie_detail_cache_controller.py` | 29 | Montagem, leitura, expiração, quando o cache não grava, tradução, invalidação, estatísticas, limpeza. |
| `tests/test_movie_prepopulate_controller.py` | 26 | Um filme, todos os filmes, estatísticas e cálculo de cobertura. |
| `tests/test_recommendations_controller.py` | 32 | Listagens, busca, adição, adição em lote, posição, duplicados, remoção. |
| `tests/test_favorites_controller.py` | 13 | Busca, filtros, paginação, listas de países e anos. |
| `tests/test_home_controller.py` | 12 | Cards, primeira imagem, falha do S3, filtros, paginação. |
| `tests/test_images_controller.py` | 9 | Listagem, legendas, ordenação, `404` e `500`. |
| `tests/test_generate_blogpost_controller.py` | 10 | Busca, `404` em busca vazia, leitura por `tconst`. |
| `tests/test_personal_opinion_controller.py` | 18 | Busca, leitura, atualização e seus códigos. |
| `tests/test_write_review_controller.py` | 13 | Busca (incluindo o filtro `content`), leitura. |

São 274 funções de teste. Com as parametrizações (`@pytest.mark.parametrize`), o pytest executa 326
casos.

Os testes de controller chamam as funções do controller diretamente e conferem o par
`(dicionário, código)`. Os testes de `test_app.py` usam `app.test_client()` e passam pela rota.

Um padrão que se repete em quase todos os arquivos: um teste com a fixture `database_down` confere
que o banco indisponível vira `500` (ou `status: "error"`, na pré-população).

## Fixtures compartilhadas (`tests/conftest.py`)

### Credenciais falsas

O `conftest.py` grava credenciais falsas em `os.environ` **antes** de importar `config`:

| Variável | Valor nos testes |
|---|---|
| `MONGODB_CONNECTION_STRING` | `mongodb://offline.invalid:27017` |
| `MONGODB_DATABASE` | `test` |
| `AWS_ACCESS_KEY_ID` | `fake-aws-key-id` |
| `AWS_SECRET_ACCESS_KEY` | `fake-aws-secret` |
| `BUCKET_NAME` | `test-bucket` |
| `OPENAI_API_KEY` | `fake-openai-key` |
| `SPOTIFY_CLIENT_ID` | `fake-spotify-id` |
| `SPOTIFY_CLIENT_SECRET` | `fake-spotify-secret` |

Como o `load_dotenv` não sobrescreve variáveis já definidas, um `.env` real no diretório não vaza
para os testes.

A fixture `fake_credentials` (automática, em todo teste) repete essas atribuições no ambiente e em
cada módulo que guardou uma cópia da credencial com `from config import ...`. A lista desses módulos
está em `CREDENTIAL_HOLDERS`. Isso garante que um teste que apague uma chave (para simular "sem
OpenAI", por exemplo) não afete o teste seguinte.

`OPENAI_MODEL` não é alterado pelo `conftest.py`. Nos testes vale o padrão de `config.py`, ou o valor
que estiver no ambiente ou no `.env` de quem roda.

### `mongo` (automática)

Troca `config.get_mongo_client` por uma função que devolve um `mongomock.MongoClient()` novo, criado
para aquele teste. Todo controller recebe coleções em memória, vazias no começo de cada teste. A
fixture devolve o banco `test`, que os testes usam para preparar documentos e conferir o que foi
gravado.

### `no_external_calls` (automática)

É a guarda da suíte. Ela substitui cada ponto de entrada externo por uma função que anota a tentativa
e lança `AssertionError`:

| Alvo | O que barra |
|---|---|
| `directors.controller.OpenAI`, `music.controller.OpenAI`, `openai.OpenAI` | Criação do cliente da OpenAI. O terceiro cobre o `movie_detail_cache`, que importa `OpenAI` dentro das funções. |
| `spotipy.Spotify`, `music.controller.SpotifyClientCredentials` | Criação do cliente do Spotify. |
| `boto3.client` | Criação do cliente do S3. |
| `requests.get`, `requests.Session.request` | Requisições HTTP (IMDB e qualquer outra). |
| `socket.socket.connect`, `socket.socket.connect_ex`, `socket.getaddrinfo` | Qualquer conexão de rede, por qualquer biblioteca. |

A fixture também zera os clientes S3 guardados em `home.controller` e `images.controller`, para que
um cliente falso de um teste não passe para o seguinte.

**Por que anotar a tentativa, além de lançar o erro.** Os controllers capturam quase todas as
exceções e seguem com um valor de falha. Só lançar o erro não derrubaria o teste: o controller
engoliria a exceção e o teste poderia passar por engano. Por isso, depois de cada teste, a fixture
confere a lista de tentativas e falha o teste se houver alguma:

```python
yield attempts
assert not attempts, f"unmocked external calls: {attempts}"
```

O resultado prático: um teste só passa se toda chamada externa do caminho exercitado tiver sido
substituída de propósito por um dublê.

### `database_down`

Faz `config.get_mongo_client` devolver `None`, simulando o MongoDB inacessível.

### `fake_openai` e `FakeOpenAI`

`fake_openai` devolve a classe `FakeOpenAI`, um dublê de `openai.OpenAI`:

- `fake_openai(reply="texto")` responde toda chamada de chat com esse texto;
- `fake_openai(error=Exception(...))` lança o erro em toda chamada;
- `api_keys` guarda as chaves com que o cliente foi criado;
- `requests` guarda os argumentos de cada chamada (`model`, `messages`, `max_tokens` etc.);
- `prompts` devolve a última mensagem de cada chamada, para conferir o texto enviado.

## Dublês de cada arquivo

| Arquivo | Dublê | Como funciona |
|---|---|---|
| `test_directors_controller.py` | `imdb` | Serve páginas do IMDB a partir de um mapa `{url: html ou exceção}` e devolve a lista de URLs pedidas. `imdb_with_godard` já traz uma página de filme e uma de diretor. |
| `test_music_controller.py` | `FakeSpotify` e `spotify` | Responde `search` a partir de um mapa `{consulta: faixa ou exceção}` e guarda as consultas feitas. |
| `test_music_controller.py` | `gpt` | Instala um `FakeOpenAI` no controller de música. |
| `test_images_controller.py`, `test_home_controller.py`, `test_app.py` | `FakeS3` e `s3` | Responde `list_objects_v2` e `get_object_tagging` com objetos e tags preparados, ou lança um erro. |
| `test_movie_detail_cache_controller.py`, `test_movie_prepopulate_controller.py` | `lookups` | Troca `get_director_info` e `get_movie_soundtrack` por funções que anotam os argumentos e devolvem respostas configuráveis. |
| `test_recommendations_controller.py`, `test_app.py` | `prepopulate`, `broken_prepopulate` | Troca `prepopulate_movie_data` por uma função que anota as chamadas, ou que lança erro. |
| `test_app.py` | `no_openai` | Zera `OPENAI_API_KEY` nos controllers de diretores e de música. |
| `test_app.py` | `client` | `app.test_client()`. |

Alguns testes de `movie_detail_cache` e `movie_prepopulate` não usam `lookups` e exercitam os
controllers reais de diretores e trilhas de ponta a ponta, com OpenAI, Spotify e IMDB substituídos
por dublês.

## O que a suíte não cobre

- **Nenhuma chamada real.** OpenAI, Spotify, S3, IMDB e MongoDB são sempre dublês. A suíte confirma a
  lógica do código em volta das integrações, não as integrações.
- **O modelo da OpenAI.** A troca para `gpt-5.6-terra` não foi validada com chamada real. Um único
  teste confere que o nome do modelo configurado é repassado.
- **Diferenças entre `mongomock` e o MongoDB real.** Comportamentos como `skip` negativo, ordenação
  com tipos mistos e operadores menos comuns podem diferir. Não verificado.
- **O HTML atual do IMDB.** Os testes usam trechos de HTML escritos à mão.
- **O script `process_all_movies.py`.**
- **Cobertura de linhas.** O projeto não mede cobertura (não há `pytest-cov` nas dependências). O
  README diz que a suíte cobre todos os controllers e as rotas; o percentual é não verificado.

## CI

Arquivo: `.github/workflows/ci.yml`. O workflow `CI` roda a cada `push` e a cada `pull_request`, em
qualquer branch, com um único job (`test`) em `ubuntu-latest`.

| Passo | O que faz |
|---|---|
| `actions/checkout@v4` | Baixa o repositório. |
| `actions/setup-python@v5` | Instala o Python 3.11, com cache do `pip` baseado nos arquivos `requirements*.txt`. |
| Install dependencies | `pip install -r requirements-dev.txt` |
| Check formatting | `black --check .` |
| Run tests | `python -m pytest` |

O workflow não usa nenhum segredo: como a suíte é offline, não precisa de credenciais. Ele não
publica a aplicação.

O Black ignora a pasta `.claude/` (configurado em `pyproject.toml`).
