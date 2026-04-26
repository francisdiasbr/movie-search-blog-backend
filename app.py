import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_restx import Api

from directors.routes import directors_bp
from home.routes import home_bp
from favorites.routes import favorites_bp
from generate_blogpost.routes import generate_blogpost_bp
from images.routes import images_bp
from movie_detail_cache.routes import movie_detail_cache_bp
from movie_prepopulate.routes import movie_prepopulate_bp
from music.routes import music_bp
from personal_opinion.routes import personal_opinion_bp
from recommendations.routes import recommendations_bp
from write_review.routes import write_review_bp

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Access-Control-Allow-Origin"],
    expose_headers=["Content-Type", "X-Total-Count"],
    supports_credentials=True,
    max_age=3600,
)

api = Api(
    app,
    title="Movie Search Blog API",
    version="1.0",
    description="API do blog de filmes",
    doc="/docs",
)

logging.getLogger("pymongo").setLevel(logging.WARNING)


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "message": "Movie Search Blog API is running",
        "docs": "/docs",
        "version": "1.0",
    })


# Register namespaces
api.add_namespace(home_bp.api, path="/api/home")
api.add_namespace(directors_bp.api, path="/api/directors")
api.add_namespace(favorites_bp.api, path="/api/favorites")
api.add_namespace(generate_blogpost_bp.api, path="/api/generate-blogpost")
api.add_namespace(images_bp.api, path="/api/images")
api.add_namespace(movie_detail_cache_bp.api, path="/api/movie-detail")
api.add_namespace(movie_prepopulate_bp.api, path="/api/prepopulate")
api.add_namespace(music_bp.api, path="/api/music")
api.add_namespace(personal_opinion_bp.api, path="/api/personal-opinion")
api.add_namespace(recommendations_bp.api, path="/api/recommendations")
api.add_namespace(write_review_bp.api, path="/api/write-review")

# Register blueprints
app.register_blueprint(home_bp, url_prefix="/api/home")
app.register_blueprint(directors_bp, url_prefix="/api/directors")
app.register_blueprint(favorites_bp, url_prefix="/api/favorites")
app.register_blueprint(generate_blogpost_bp, url_prefix="/api/generate-blogpost")
app.register_blueprint(images_bp, url_prefix="/api/images")
app.register_blueprint(movie_detail_cache_bp, url_prefix="/api/movie-detail")
app.register_blueprint(movie_prepopulate_bp, url_prefix="/api/prepopulate")
app.register_blueprint(music_bp, url_prefix="/api/music")
app.register_blueprint(personal_opinion_bp, url_prefix="/api/personal-opinion")
app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")
app.register_blueprint(write_review_bp, url_prefix="/api/write-review")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    app.run(debug=True, port=port, host=host, threaded=True)
