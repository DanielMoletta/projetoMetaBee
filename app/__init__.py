# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Inicializa as extensões
db = SQLAlchemy()
login = LoginManager()
# Informa ao Flask-Login qual é a rota de login.
# 'main.login' -> 'login' é a função, 'main' é o nome do Blueprint.
login.login_view = 'main.login'


def create_app(config_class=Config):
    """
    Cria e configura uma instância da aplicação Flask.
    Este é o padrão Application Factory.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Carrega as configurações a partir da classe Config
    app.config.from_object(config_class)

    # Inicializa as extensões com a aplicação
    db.init_app(app)
    login.init_app(app)

    # Importa e registra o Blueprint do arquivo de rotas
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # É importante que o models seja importado para que o user_loader funcione
    from app import models

    # Comando para criar o banco de dados e as tabelas
    with app.app_context():
        db.create_all()

    return app