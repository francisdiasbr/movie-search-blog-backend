# Movie Search Blog — backend

[![CI](https://github.com/francisdiasbr/movie-search-blog-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/francisdiasbr/movie-search-blog-backend/actions/workflows/ci.yml)

> 🇧🇷 The main version of this document is in Portuguese: [README.md](README.md). It has the
> architecture diagram and the full list of routes.

REST API of the **Movie Search blog**, a personal blog about cinema: authored reviews, posts,
personal opinions, recommendations, directors and the soundtrack of each film. It serves a React and
TypeScript frontend that lives in a separate repository
([movie-search-blog](https://github.com/francisdiasbr/movie-search-blog)).

Built with **Python 3.11, Flask, flask-restx, MongoDB Atlas, AWS S3, the OpenAI API and the Spotify
API**.

## What it does

Each feature is a folder with `routes.py` (flask-restx namespace and routes) and `controller.py`
(business rules and database access); `app.py` registers one namespace per feature under `/api`.
Besides reading and writing to MongoDB, the API:

- lists a film's images on **S3** and builds their public URLs;
- generates director biographies, soundtrack descriptions and Portuguese/English translations with
  the **OpenAI API** (the model is set by `OPENAI_MODEL`);
- looks up soundtrack tracks on **Spotify**;
- caches film, director and soundtrack as a single document for 24 hours, so the blog's detail page
  opens with one request;
- pre-populates director and soundtrack data before a film is first opened.

Interactive documentation (Swagger UI) is served at `/docs`.

## Running locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # MongoDB Atlas, AWS S3, OpenAI and Spotify settings
python app.py             # http://localhost:5001, Swagger at /docs
```

The API is **not deployed** at the moment. The `Procfile` (`gunicorn app:app`) keeps it ready for
platforms that follow that convention.

## Tests and CI

```bash
pip install -r requirements-dev.txt      # pytest, mongomock and Black
python -m pytest
python -m black --check .
```

The suite runs offline in under a second: MongoDB is simulated in memory with mongomock, credentials
are replaced by fake values, and any real call to OpenAI, Spotify, S3 or the network fails the test.
It covers every controller and, through Flask's test client, the routes.

GitHub Actions runs the formatting check and the suite on every push and pull request
([`ci.yml`](.github/workflows/ci.yml)).
