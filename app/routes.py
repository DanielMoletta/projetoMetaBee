from flask import render_template, flash, redirect, url_for, Blueprint, request, jsonify
from app import db
from app.forms import LoginForm, TagRegistrationForm
from app.models import User, RfidTag, AccessLog
from flask_login import current_user, login_user, logout_user, login_required
import requests
import os

main = Blueprint('main', __name__)

# --- Funções Auxiliares ---

def send_discord_webhook(uid, username, status):
    """Função auxiliar para enviar a notificação para o Discord."""
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("Webhook do Discord não configurado.")
        return

    if status == "Acesso Negado":
        color = 15158332  # Vermelho
        title = "❌ Acesso Negado: Tag Desconhecida"
        description = f"Uma tag RFID não registrada tentou acessar o sistema."
    else:
        color = 3066993  # Verde
        title = f"✅ Acesso Garantido: {username}"
        description = f"O usuário **{username}** acessou as instalações."

    payload = {
        "username": "Controle de Acesso",
        "avatar_url": "https://i.imgur.com/R6yYwko.png",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "fields": [
                {"name": "UID da Tag", "value": f"`{uid}`", "inline": False}
            ],
            "footer": {"text": "Sistema de Monitoramento Automatizado (via Flask & ESP32)"}
        }]
    }
    try:
        requests.post(webhook_url, json=payload)
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar webhook para o Discord: {e}")

# --- Endpoints da API ---

@main.route('/api/rfid_log', methods=['POST'])
def rfid_log():
    """Recebe o UID do ESP32, determina o status, registra e notifica."""
    data = request.get_json()
    if not data or 'uid' not in data:
        return jsonify({'status': 'error', 'message': 'UID não fornecido'}), 400

    uid = data['uid']
    
    # Verifica se a tag está registrada para determinar o status e o nome
    tag = RfidTag.query.filter_by(tag_uid=uid).first()
    if tag:
        username = tag.username
        status = "Acesso Garantido"
    else:
        username = "Desconhecido"
        status = "Acesso Negado"
    
    # Cria o registro de log com o status correto
    new_log = AccessLog(tag_uid=uid, username=username, status=status)
    db.session.add(new_log)
    db.session.commit()
    
    # Envia a notificação para o Discord
    send_discord_webhook(uid, username, status)
    
    return jsonify({'status': 'success', 'message': 'Log recebido'}), 201

@main.route('/api/get_logs')
@login_required
def get_logs():
    """Fornece os 5 logs mais recentes, incluindo o status, para o frontend."""
    logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(5).all()
    log_list = [
        {
            'username': log.username,
            'tag_uid': log.tag_uid,
            'timestamp': log.timestamp.astimezone().strftime('%d/%m/%Y %H:%M:%S'),
            'status': log.status  # Adiciona o status à resposta da API
        }
        for log in logs
    ]
    return jsonify(log_list)

# --- Rotas da Interface Web (sem alterações) ---

@main.route('/')
@main.route('/index')
@login_required
def index():
    tags = RfidTag.query.all()
    return render_template('index.html', title='Página Inicial', tags=tags)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('main.login'))
        
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
        
    return render_template('login.html', title='Entrar', form=form)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/register_tag', methods=['GET', 'POST'])
@login_required
def register_tag():
    form = TagRegistrationForm()
    if form.validate_on_submit():
        tag = RfidTag(tag_uid=form.tag_uid.data, username=form.username.data)
        db.session.add(tag)
        db.session.commit()
        flash('Nova tag RFID registrada com sucesso!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('register_tag.html', title='Registrar Tag RFID', form=form)

