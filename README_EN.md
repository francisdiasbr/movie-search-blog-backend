# Movie Search Blog Backend

<div>
  <img src="https://img.shields.io/badge/status-online-brightgreen" alt="Website" />
  <img src="https://img.shields.io/github/last-commit/francisdiasbr/movie-search-blog-backend" alt="GitHub last commit" />
  <img src="https://img.shields.io/github/v/release/francisdiasbr/movie-search-blog-backend" alt="GitHub release (latest by date)" />
  <img src="https://img.shields.io/github/languages/top/francisdiasbr/movie-search-blog-backend" alt="GitHub top language" />
</div>

<br/>

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

## Infrastructure

The project is hosted on the following infrastructure:

- **Backend**: Flask application hosted on Heroku
- **Image Storage**: Amazon S3 for blog post image storage
- **Database**: MongoDB Atlas for data persistence

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

### Base URL
- Development: http://localhost:5000
- Production: https://your-app.herokuapp.com

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
Create a `.env` file in the root of the project and define the following variables:

- **MongoDB**:
  - `MONGODB_CONNECTION_STRING`: MongoDB connection string.
  - `MONGODB_DATABASE`: MongoDB database name.

- **AWS S3**:
  - `AWS_ACCESS_KEY_ID`: AWS access key ID.
  - `AWS_SECRET_ACCESS_KEY`: AWS secret access key.
  - `BUCKET_NAME`: S3 bucket name.

Example `.env` file:
```
MONGODB_CONNECTION_STRING="mongodb+srv://<username>:<password>@cluster0.mongodb.net/"
MONGODB_DATABASE="movie-search"
AWS_ACCESS_KEY_ID="your-access-key-id"
AWS_SECRET_ACCESS_KEY="your-secret-access-key"
BUCKET_NAME="your-bucket-name"
```

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
