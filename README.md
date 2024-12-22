# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual

# No macOS/Linux
source venv/bin/activate

# No Windows
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Rode o servidor
python app.py