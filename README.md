# Movie Search Blog Backend

[Read in English](README_EN.md)

API para busca e gerenciamento de filmes e posts de blog.

## Índice

- [Estrutura do Projeto](#estrutura-do-projeto)
- [Configuração](#configuração)
  - [Ambiente Virtual](#ambiente-virtual)
  - [Dependências](#dependências)
  - [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Executando o Projeto](#executando-o-projeto)
- [Documentação da API](#documentação-da-api)
  - [Endpoints Favoritos](#endpoints-favoritos)
  - [Endpoints Blog Posts](#endpoints-blog-posts)
- [Desenvolvimento](#desenvolvimento)
  - [Estrutura dos Módulos](#estrutura-dos-módulos)
  - [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

## Estrutura do Projeto

```
movie-search-blog-backend/
├── app.py # Aplicação principal
├── config.py # Configurações (MongoDB, AWS, etc)
├── requirements.txt # Dependências do projeto
├── favorites/ # Módulo de filmes favoritos
│ ├── init.py
│ ├── controller.py # Lógica de negócios
│ ├── models.py # Modelos Swagger
│ └── routes.py # Rotas da API
└── blogposts/ # Módulo de posts do blog
├── init.py
├── controller.py # Lógica de negócios
├── models.py # Modelos Swagger
└── routes.py # Rotas da API
```

## Documentação da API
A documentação Swagger está disponível em http://localhost:5000/docs

### Endpoints Favoritos
- POST /api/favorites/search - Pesquisa filmes favoritos
- GET /api/favorites/tconst - Obtém um filme favorito
- POST /api/favorites/tconst - Adiciona um filme aos favoritos
- PUT /api/favorites/tconst - Atualiza um filme favorito
- DELETE /api/favorites/tconst - Remove um filme dos favoritos

### Endpoints Blog Posts
- POST /api/blogposts/search - Pesquisa posts do blog
- GET /api/blogposts/tconst - Obtém um post específico
- GET /api/blogposts/images/tconst - Obtém as imagens de um post


## Configuração

### Crie um ambiente virtual
`python -m venv venv`

### Ative o ambiente virtual

#### No macOS/Linux
`source venv/bin/activate`

#### No Windows
`venv\Scripts\activate`

### Dependências
`pip install -r requirements.txt`

### Variáveis de Ambiente
`nome_do_seu_bucket`

## Executando o Projeto
`python app.py`

## Desenvolvimento

### Estrutura dos Módulos
Cada módulo (favorites e blogposts) segue a mesma estrutura:
- models.py: Define os modelos Swagger para documentação da API
- routes.py: Define as rotas e endpoints da API
- controller.py: Contém a lógica de negócios e interação com o banco de dados

### Tecnologias Utilizadas
- Flask: Framework web
- Flask-RESTX: Extensão para APIs RESTful e documentação Swagger
- PyMongo: Driver MongoDB
- Boto3: SDK AWS para Python
- Python-dotenv: Gerenciamento de variáveis de ambiente