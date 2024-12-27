from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from favorites.routes import favorites_bp, api as favorites_api
from blogposts.routes import blogposts_bp, api as blogposts_api

app = Flask(__name__)
CORS(app)

# Criar a API
api = Api(app,
    title='Movie Search API',
    version='1.0',
    description='API para busca e gerenciamento de filmes'
)

# Registrar os namespaces
api.add_namespace(favorites_api, path='/api/favorites')
api.add_namespace(blogposts_api, path='/api/blogposts')

# Registrar os blueprints
app.register_blueprint(favorites_bp, url_prefix='/api/favorites')
app.register_blueprint(blogposts_bp, url_prefix='/api/blogposts')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port, host='0.0.0.0')