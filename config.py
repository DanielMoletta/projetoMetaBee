import os
from dotenv import load_dotenv

# Encontra o caminho absoluto para o diretório raiz do projeto
basedir = os.path.abspath(os.path.dirname(__file__))

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Classe de configuração base."""
    # Pega a SECRET_KEY do ambiente ou usa uma chave padrão (NÃO FAÇA ISSO EM PRODUÇÃO)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Configuração do banco de dados SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False