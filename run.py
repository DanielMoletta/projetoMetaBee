from app import create_app

# Cria a instância da aplicação usando a factory
app = create_app()

if __name__ == '__main__':
    # Executa a aplicação com o servidor de desenvolvimento do Flask
    # debug=True: Ativa o modo de depuração para mostrar erros detalhados.
    # host='0.0.0.0': **MUITO IMPORTANTE!** Faz o servidor ficar visível
    # para outros dispositivos na sua rede local, como o seu ESP32.
    app.run(debug=True, host='0.0.0.0')