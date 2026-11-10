# Pontos de atenção

Lista do que a leitura do código mostrou de limitação, inconsistência ou risco. Nada aqui foi
corrigido; o objetivo é registrar. Cada item aponta o arquivo e, quando há, o documento que descreve
o comportamento em detalhe.

Os itens marcados como **simulado** foram reproduzidos localmente com o cliente de teste do Flask e
`mongomock`, sem rede. Os demais vêm só da leitura.

## Estado geral

- **A API não está publicada.** Render e Heroku estão fora do ar.
- **A troca do modelo da OpenAI não foi validada com chamada real.** O padrão `gpt-5.6-terra` e os
  parâmetros `max_tokens` e `temperature` nunca foram exercitados contra a API. Uma recusa seria
  silenciosa. Veja [integracoes.md](integracoes.md).
- **Há uma alteração não commitada em `requirements.txt`** (`pymongo==4.10.1` para
  `pymongo>=4.14.5`). O CI roda com o que está commitado.

## Segurança e exposição

- **Nenhuma rota tem autenticação.** Isso inclui `DELETE /api/recommendations/clear`,
  `DELETE /api/directors/<nome>`, `DELETE /api/music/soundtrack`,
  `PUT /api/personal-opinion/<tconst>`, `POST /api/recommendations/add` e `POST /api/prepopulate/all`.
  As rotas de geração e de pré-população consomem crédito da OpenAI a cada chamada.
- **CORS aberto com credenciais.** `origins: "*"` junto com `supports_credentials=True` (`app.py`).
- **Filtros repassados ao MongoDB.** As buscas de `favorites`, `home`, `write_review`,
  `generate_blogpost` e `personal_opinion` aceitam um objeto `filters` e o entregam ao `find` sem
  restringir chaves nem operadores.
- **Texto de busca usado como expressão regular, sem escape.** Um termo inválido causa `500`
  (simulado em `POST /api/favorites/search` com `search_term: "("`).
- **`debug=True` fixo** quando o app é iniciado com `python app.py`.
- **Mensagens de exceção na resposta.** `favorites`, `generate_blogpost`, `recommendations` (adição) e
  `movie_prepopulate` devolvem o texto da exceção do Python a quem chamou.

## Comportamentos que podem surpreender

- **`generate_blogpost` não gera nada.** O módulo só lê a coleção `blogposts`. O nome da pasta e a
  descrição do namespace falam em geração.
  ([funcionalidades/generate-blogpost.md](funcionalidades/generate-blogpost.md))
- **`/api/recommendations/random` não é aleatória.** Devolve tudo, por `position`. Está documentado
  no código. ([funcionalidades/recommendations.md](funcionalidades/recommendations.md))
- **Busca de posts vazia responde `404`,** enquanto as outras buscas respondem `200` com lista vazia.
- **Quatro formatos de erro diferentes** entre os módulos. ([arquitetura.md](arquitetura.md))
- **Rota inexistente responde HTML,** não JSON (simulado).
- **`/api/personal-opinion` sem barra final responde `308`** (simulado). O README lista o caminho sem
  a barra.

## Defeitos prováveis

- **Campo de data do BSON derruba a serialização.** `write_review`, `generate_blogpost`,
  `personal_opinion`, `favorites` e `recommendations` devolvem os documentos como vieram do banco. Se
  um documento tiver um campo do tipo data (por exemplo `created_at`), a resposta é `500` com
  `{"message": "Internal Server Error"}` (simulado nas cinco coleções). O `home` trata esse caso para
  a mesma coleção de resenhas, o que sugere que há datas do BSON nos dados reais. Se as rotas falham
  com os dados reais é não verificado.
- **Trilha gravada no idioma da primeira requisição.** Uma trilha gerada com `language=en` fica com
  textos em inglês e é servida assim para `pt`. (`music/controller.py`;
  [funcionalidades/music.md](funcionalidades/music.md))
- **Tradução que falha é guardada no cache de inglês.** O cache de detalhe não distingue texto
  traduzido de texto que voltou em português por falha. (`movie_detail_cache/controller.py`)
- **`language` não validado em `movie-detail` e `prepopulate`.** Um idioma fora de `pt` e `en` cria
  uma chave de cache própria, com biografia traduzida para inglês e descrição pedida no idioma
  informado.
- **Filme com vários diretores nunca é `already_exists` na pré-população.** A checagem procura os
  nomes juntos como um só. (`movie_prepopulate/controller.py`, `_check_existing_director`)
- **`/add` anuncia sucesso da pré-população sem olhar o resultado.** A mensagem
  `"Filme adicionado e dados pré-populados com sucesso"` sai mesmo quando `prepopulate.status` é
  `error`. (`recommendations/controller.py`)
- **`bulk-add` com lista só de itens inválidos** responde `"Todos os filmes já existem na base de
  dados"`.
- **Trilha com todas as faixas sem título** é gravada com `tracks` vazio e `source: "gpt_spotify"`.
- **Corpo JSON em formato de lista causa `500` genérico** em `POST /api/write-review/search`,
  `POST /api/prepopulate/all` e `POST /api/prepopulate/movie` (simulado nas duas primeiras).
- **`page` e `page_size` sem validação** em `home`, `write_review`, `generate_blogpost` e
  `personal_opinion`. Um valor string causa `500` (simulado em `home` e `generate_blogpost`). Só o
  `favorites` valida.
- **Resultados de `/api/prepopulate/all` sem identificação do filme.**
- **A primeira imagem do `home` e a primeira do `images` seguem critérios diferentes:** ordem de
  listagem do S3 em um, data de modificação no outro.
- **A listagem de imagens não trata paginação do S3.**
- **Primeiro resultado do Spotify aceito sem conferência** de título e artista.

## Concorrência e consistência

- **O código não cria índices.** Não há unicidade garantida em `recommendations.tconst`,
  `directors.name`, `movie_soundtracks.cache_key` nem `movie_detail_cache.cache_key`. As checagens de
  duplicidade são uma leitura seguida de uma escrita. Se há índices criados direto no banco é não
  verificado.
- **Não há índice TTL no cache.** Caches expirados ficam na coleção até a próxima leitura do filme ou
  uma chamada a `/cleanup`.
- **Remoções não propagam.** Apagar uma recomendação, um diretor ou uma trilha não invalida o cache
  de detalhe que guarda uma cópia.
- **Chamadas externas dentro da requisição.** `/api/prepopulate/all` e `/api/recommendations/bulk-add`
  com pré-população seguram a requisição HTTP até todas as chamadas externas terminarem. Com gunicorn
  nas opções padrão, se isso estoura o tempo limite do worker é não verificado.

## Observabilidade

- **Exceções são engolidas sem log.** Quase todo `except Exception` devolve um valor de falha e não
  registra nada. As únicas mensagens de console são os `print` de `config.py` sobre a conexão com o
  MongoDB.
- **Falhas de integração são indistinguíveis.** Chave inválida, modelo recusado, limite de uso e
  tempo limite produzem a mesma resposta.

## Código

- **Tradução duplicada.** Há três funções de tradução de biografia e de descrição com prompts
  parecidos: em `directors`, em `music` e em `movie_detail_cache`. Os tempos limite diferem (a de
  `directors` não tem).
- **Cliente S3 duplicado** em `images/controller.py` e `home/controller.py`.
- **Ramos idênticos** em `_create_combined_directors_bio` (`directors/controller.py`), para `pt` e
  para os outros idiomas.
- **Código sem uso.** `get_all_write_reviews` não tem rota. Há importações não usadas: `requests` em
  `music/controller.py`; `asyncio` e `datetime` em `movie_prepopulate/controller.py`; `json` em
  `movie_detail_cache/controller.py`.
  O parâmetro `language` de `get_all_recommendations` e de `_get_movie_data` não é usado.
- **`sys.path.append`** no topo de cinco controllers, desnecessário com `pythonpath = .` nos testes e
  com a execução a partir da raiz.
- **Argumentos padrão mutáveis** em `get_favorited_movies` (`filters={}`, `sorters=[...]`).
- **Mensagens copiadas.** `write_review` usa mensagens de erro e docstrings de "opinião pessoal".
- **Modelos do Swagger soltos.** Nenhuma rota usa `marshal_with` nem validação; alguns modelos listam
  campos que o código não lê (`FavoriteMovie`, `BlogPost`) e omitem campos que a resposta tem
  (`placeholder`, `directors`, `cache_key`, `_id`).
- **`X-Total-Count`** está nos cabeçalhos expostos do CORS e nenhuma rota o envia.
- **`requirements.txt` sem quebra de linha no final,** assim como o `Procfile`.

## Diferenças entre o README e o código

| README | Código |
|---|---|
| Tabela de rotas lista `GET /personal-opinion` e `POST /personal-opinion`. | As rotas são `/api/personal-opinion/`, com barra final; sem ela, a resposta é `308`. |
| "Traduções entre português e inglês." | O código só traduz de português para inglês. |
| A pasta `generate_blogpost` é descrita como "posts do blog". | Confere: o módulo só lê posts. O que destoa é o nome da pasta e a descrição do namespace no Swagger, que falam em geração. |
| "Guardado por 24 horas." | O cache só é gravado quando diretor e trilha são definitivos; caso contrário, cada requisição refaz a montagem. |
| Diretores: "Lê (gerando a biografia, se preciso)." | Quando a geração falha, a rota responde `200` com biografia genérica e `placeholder: true`. O README não cita esse campo, nem `source: "gpt"` nas trilhas. |
| Tabela de variáveis. | `PORT` e `FLASK_HOST` também são lidas (`app.py`) e não aparecem no README nem no `.env.example`. |

Fora do README: o docstring de `tests/conftest.py` cita TMDB, e nenhum código chama o TMDB.

O restante do README confere com o código: a lista de rotas, as variáveis de ambiente, o comando do
`Procfile`, a descrição dos testes e do CI.
