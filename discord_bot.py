import discord
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

# --- Configurações ---
# Token do Bot do Discord (Adicione no seu arquivo .env como DISCORD_BOT_TOKEN=seu_token)
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Senha secreta compartilhada com o Flask (Adicione no .env como OP_SECRET=sua_senha)
OP_SECRET = os.getenv('OP_SECRET', 'senha_padrao_segura')

# URL local do Flask (Como o bot roda no mesmo PC do servidor, usamos localhost)
# Se o bot rodar em outro lugar, use a URL do Ngrok.
FLASK_API_URL = "http://127.0.0.1:5000/api/trigger_door"

# Configuração de Intents (Necessário para bots modernos lerem comandos)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como: {bot.user.name}')
    print('Pronto para receber comandos!')

@bot.command(name='abrir')
async def abrir_porta(ctx):
    """Comando para abrir a porta remotamente via Flask -> ESP32."""
    
    # Feedback imediato para o usuário
    msg = await ctx.send("🔄 Processando solicitação de abertura...")
    
    try:
        # Prepara os dados para enviar ao Flask
        payload = {'secret': OP_SECRET}
        
        # Envia requisição POST para o backend Flask
        response = requests.post(FLASK_API_URL, json=payload)
        
        if response.status_code == 200:
            await msg.edit(content="✅ **Comando Enviado!** A porta deve abrir em instantes.")
        elif response.status_code == 403:
            await msg.edit(content="⛔ **Erro de Autorização:** Chave secreta incorreta no sistema.")
        else:
            await msg.edit(content=f"❌ **Erro no Servidor:** Código {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        await msg.edit(content="❌ **Erro:** Não foi possível conectar ao servidor Flask. Ele está rodando?")
    except Exception as e:
        await msg.edit(content=f"❌ **Erro desconhecido:** {str(e)}")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Token do Discord não encontrado no arquivo .env")
    else:
        bot.run(TOKEN)