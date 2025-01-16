from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from favorites.routes import favorites_bp, api as favorites_api
from generate_blogpost.routes import generate_blogpost_bp, api as blogposts_api
from images.routes import images_bp, api as images_api
from personal_opinion.routes import personal_opinion_bp, api as personal_opinion_api

import logging

app = Flask(__name__)
CORS(app)

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
api.add_namespace(favorites_api, path='/api/favorites')
api.add_namespace(blogposts_api, path='/api/generate-blogpost')
api.add_namespace(images_api, path='/api/images')
api.add_namespace(personal_opinion_api, path='/api/personal-opinion')
# Register blueprints
app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
app.register_blueprint(generate_blogpost_bp, url_prefix='/api/generate-blogpost')
app.register_blueprint(images_bp, url_prefix='/api/images')
app.register_blueprint(personal_opinion_bp, url_prefix='/api/personal-opinion')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port, host='0.0.0.0')