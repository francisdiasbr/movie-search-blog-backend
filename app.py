from flask import Flask, jsonify
from flask_cors import CORS
from flask_restx import Api
from directors.routes import directors_bp, api as directors_api
from favorites.routes import favorites_bp, api as favorites_api
from generate_blogpost.routes import generate_blogpost_bp, api as blogposts_api
from images.routes import images_bp, api as images_api
from music.routes import music_bp, api as music_api
from movie_detail_cache.routes import movie_detail_cache_bp
from movie_prepopulate.routes import movie_prepopulate_bp
from personal_opinion.routes import personal_opinion_bp, api as personal_opinion_api
from recommendations.routes import recommendations_bp, api as recommendations_api
from write_review.routes import write_review_bp, api as write_review_api

import logging

app = Flask(__name__)

# Configure CORS with valid headers and origins
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Access-Control-Allow-Origin"],
    expose_headers=["Content-Type", "X-Total-Count"],
    supports_credentials=True,
    max_age=3600
)

# Create API
api = Api(app,
    title='Movie Search API',
    version='1.0',
    description='API para busca e gerenciamento de filmes'
)

# Configure PyMongo logging level
logging.getLogger('pymongo').setLevel(logging.WARNING)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Movie Search API is running",
        "docs": "/docs",
        "version": "1.0",
    })

# Register namespaces
api.add_namespace(directors_api, path='/api/directors')
api.add_namespace(favorites_api, path='/api/favorites')
api.add_namespace(blogposts_api, path='/api/generate-blogpost')
api.add_namespace(images_api, path='/api/images')
api.add_namespace(music_api, path='/api/music')
api.add_namespace(personal_opinion_api, path='/api/personal-opinion')
api.add_namespace(recommendations_api, path='/api/recommendations')
api.add_namespace(write_review_api, path='/api/write-review')


# Register blueprints
app.register_blueprint(directors_bp, url_prefix='/api/directors')
app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
app.register_blueprint(generate_blogpost_bp, url_prefix='/api/generate-blogpost')
app.register_blueprint(images_bp, url_prefix='/api/images')
app.register_blueprint(music_bp, url_prefix='/api/music')
app.register_blueprint(movie_detail_cache_bp, url_prefix='/api')
app.register_blueprint(movie_prepopulate_bp, url_prefix='/api')
app.register_blueprint(personal_opinion_bp, url_prefix='/api/personal-opinion')
app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
app.register_blueprint(write_review_bp, url_prefix='/api/write-review')


if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    app.run(debug=True, port=port, host=host, threaded=True)