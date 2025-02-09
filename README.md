# Movie Search Blog Backend

<div>
  <img src="https://img.shields.io/badge/status-online-brightgreen" alt="Website" />
  <img src="https://img.shields.io/github/last-commit/francisdiasbr/movie-search-blog-backend" alt="GitHub last commit" />
  <img src="https://img.shields.io/github/v/release/francisdiasbr/movie-search-blog-backend" alt="GitHub release (latest by date)" />
  <img src="https://img.shields.io/github/languages/top/francisdiasbr/movie-search-blog-backend" alt="GitHub top language" />
</div>

<br/>


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

## Infraestrutura

O projeto está hospedado na seguinte infraestrutura:

- **Backend**: Aplicação Flask hospedada no Heroku
- **Armazenamento de Imagens**: Amazon S3 para armazenamento de imagens dos posts
- **Banco de Dados**: MongoDB Atlas para persistência dos dados

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

### URL Base
- Desenvolvimento: http://localhost:5000
- Produção: https://seu-app.herokuapp.com

### Endpoints Favoritos
- POST /api/favorites/search - Exibe todos os filmes favoritos

### Endpoints Blog Posts
- POST /api/blogposts/search - Exibe todos os posts do blog
- GET /api/blogposts/tconst - Exibe um post específico

## Endpoints de Imagens
- GET /api/images/tconst - Exibe todas as imagens de um filme
- POST /api/images/tconst/filename - Exibe uma imagem específica de um filme


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
Crie um arquivo `.env` na raiz do projeto e defina as seguintes variáveis:

- **MongoDB**:
  - `MONGODB_CONNECTION_STRING`: String de conexão com o MongoDB.
  - `MONGODB_DATABASE`: Nome do banco de dados MongoDB.

- **AWS S3**:
  - `AWS_ACCESS_KEY_ID`: ID da chave de acesso da AWS.
  - `AWS_SECRET_ACCESS_KEY`: Chave de acesso secreta da AWS.
  - `BUCKET_NAME`: Nome do bucket S3.

Exemplo de arquivo `.env`:
```
MONGODB_CONNECTION_STRING="mongodb+srv://<username>:<password>@cluster0.mongodb.net/"
MONGODB_DATABASE="movie-search"
AWS_ACCESS_KEY_ID="your-access-key-id"
AWS_SECRET_ACCESS_KEY="your-secret-access-key"
BUCKET_NAME="your-bucket-name"
```

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
