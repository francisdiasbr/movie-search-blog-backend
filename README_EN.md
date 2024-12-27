# Movie Search Blog Backend

API for searching and managing movies and blog posts.

## Table of Contents

- [Project Structure](#project-structure)
- [Setup](#setup)
  - [Virtual Environment](#virtual-environment)
  - [Dependencies](#dependencies)
  - [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [API Documentation](#api-documentation)
  - [Favorites Endpoints](#favorites-endpoints)
  - [Blog Posts Endpoints](#blog-posts-endpoints)
- [Development](#development)
  - [Module Structure](#module-structure)
  - [Technologies Used](#technologies-used)
- [Contributing](#contributing)
- [License](#license)

## Project Structure

```
movie-search-blog-backend/
├── app.py # Main application
├── config.py # Configurations (MongoDB, AWS, etc)
├── requirements.txt # Project dependencies
├── favorites/ # Favorite movies module
│ ├── init.py
│ ├── controller.py # Business logic
│ ├── models.py # Swagger models
│ └── routes.py # API routes
└── blogposts/ # Blog posts module
├── init.py
├── controller.py # Business logic
├── models.py # Swagger models
└── routes.py # API routes
```

## API Documentation
Swagger documentation is available at http://localhost:5000/docs

### Favorites Endpoints
- POST /api/favorites/search - Search favorite movies
- GET /api/favorites/tconst - Get a favorite movie
- POST /api/favorites/tconst - Add a movie to favorites
- PUT /api/favorites/tconst - Update a favorite movie
- DELETE /api/favorites/tconst - Remove a movie from favorites

### Blog Posts Endpoints
- POST /api/blogposts/search - Search blog posts
- GET /api/blogposts/tconst - Get a specific post
- GET /api/blogposts/images/tconst - Get images of a post

## Setup

### Create a virtual environment
`python -m venv venv`

### Activate the virtual environment

#### On macOS/Linux
`source venv/bin/activate`

#### On Windows
`venv\Scripts\activate`

### Dependencies
`pip install -r requirements.txt`

### Environment Variables
`your_bucket_name`

## Running the Project
`python app.py`

## Development

### Module Structure
Each module (favorites and blogposts) follows the same structure:
- models.py: Defines Swagger models for API documentation
- routes.py: Defines API routes and endpoints
- controller.py: Contains business logic and database interaction

### Technologies Used
- Flask: Web framework
- Flask-RESTX: Extension for RESTful APIs and Swagger documentation
- PyMongo: MongoDB driver
- Boto3: AWS SDK for Python
- Python-dotenv: Environment variable management 