# Documentação técnica

Esta pasta descreve em profundidade a API do blog do Movie Search. O [README da raiz](../README.md)
dá a visão geral; aqui está o detalhe de cada camada, rota, coleção e integração.

Tudo o que está escrito aqui foi tirado da leitura do código. Onde o código não permite afirmar algo
(por exemplo, o conteúdo real do banco ou o comportamento de um serviço externo), o texto diz
**não verificado**.

Situação atual do projeto, que vale para todos os documentos:

- A API **não está publicada**. Os endereços antigos no Render e no Heroku estão fora do ar. Os
  exemplos usam `http://localhost:5001`.
- O modelo da OpenAI vem de `OPENAI_MODEL` (padrão `gpt-5.6-terra`). Essa troca de modelo **ainda não
  foi validada com uma chamada real**; a suíte de testes nunca chama a OpenAI de verdade.
- Da AWS, o projeto usa apenas o S3.

## Documentos

| Documento | O que traz |
|---|---|
| [arquitetura.md](arquitetura.md) | Camadas, inicialização do app, ciclo de uma requisição, configuração, variáveis de ambiente, convenção de erros e diagramas dos fluxos principais. |
| [funcionalidades/](funcionalidades/README.md) | Um arquivo por módulo: o que a feature faz, cada rota com parâmetros, corpo, resposta e códigos de status, o passo a passo interno, regras de negócio e casos de borda. |
| [modelo-de-dados.md](modelo-de-dados.md) | Cada coleção do MongoDB, seus campos e a origem de cada campo, e o que fica guardado no S3. |
| [integracoes.md](integracoes.md) | OpenAI, Spotify, S3, IMDB e MongoDB: o que é chamado, com quais parâmetros, como cada chamada falha e o que a API responde nesse caso. |
| [testes.md](testes.md) | Organização da suíte, fixtures, guardas contra chamadas externas, como rodar e o que o CI faz. |
| [pontos-de-atencao.md](pontos-de-atencao.md) | Limitações conhecidas, inconsistências e riscos encontrados na leitura do código, reunidos em um só lugar. |

## Funcionalidades, por módulo

| Módulo | Prefixo | Documento |
|---|---|---|
| `home` | `/api/home` | [Página inicial](funcionalidades/home.md) |
| `write_review` | `/api/write-review` | [Resenhas autorais](funcionalidades/write-review.md) |
| `generate_blogpost` | `/api/generate-blogpost` | [Posts do blog](funcionalidades/generate-blogpost.md) |
| `personal_opinion` | `/api/personal-opinion` | [Opiniões pessoais](funcionalidades/personal-opinion.md) |
| `favorites` | `/api/favorites` | [Favoritos](funcionalidades/favorites.md) |
| `recommendations` | `/api/recommendations` | [Recomendações](funcionalidades/recommendations.md) |
| `directors` | `/api/directors` | [Diretores](funcionalidades/directors.md) |
| `music` | `/api/music` | [Trilhas sonoras](funcionalidades/music.md) |
| `images` | `/api/images` | [Imagens](funcionalidades/images.md) |
| `movie_detail_cache` | `/api/movie-detail` | [Detalhe do filme e cache](funcionalidades/movie-detail-cache.md) |
| `movie_prepopulate` | `/api/prepopulate` | [Pré-população](funcionalidades/prepopulate.md) |
