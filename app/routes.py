from flask import render_template, flash, redirect, url_for, Blueprint, request, jsonify
from app import db
from app.forms import LoginForm, TagRegistrationForm
from app.models import User, RfidTag, AccessLog
from flask_login import current_user, login_user, logout_user, login_required
import requests
import os
import time # Import necessário para o controle de tempo
from datetime import datetime
import logging

main = Blueprint('main', __name__)

# Configuração de logging
logger = logging.getLogger(__name__)

# --- Variável Global para Controle da Porta ---
door_open_command = {
    "pending": False,
    "timestamp": 0
}

# --- Constantes ---
DISCORD_COLORS = {
    "Acesso Negado": 15158332,  # Vermelho
    "Acesso Garantido": 3066993  # Verde
}

DISCORD_TITLES = {
    "Acesso Negado": "❌ Acesso Negado: Tag Desconhecida",
    "Acesso Garantido": "✅ Acesso Garantido: {}"
}

# --- Funções Auxiliares ---

def send_discord_webhook(uid: str, username: str, status: str) -> None:
    """Envia notificação para o Discord de forma assíncrona."""
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("Webhook do Discord não configurado.")
        return

    color = DISCORD_COLORS.get(status, 0)
    
    if status == "Acesso Negado":
        title = DISCORD_TITLES["Acesso Negado"]
        description = "Uma tag RFID não registrada tentou acessar o sistema."
    else:
        title = DISCORD_TITLES["Acesso Garantido"].format(username)
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
            "footer": {"text": "Sistema de Monitoramento Automatizado (via Flask & ESP32)"},
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar webhook para o Discord: {e}")

def process_rfid_access(uid: str) -> tuple:
    """Processa o acesso RFID e retorna username e status."""
    tag = RfidTag.query.filter_by(tag_uid=uid).first()
    
    if tag:
        return tag.username, "Acesso Garantido"
    return "Desconhecido", "Acesso Negado"

# --- NOVOS ENDPOINTS PARA ABERTURA REMOTA ---

@main.route('/api/trigger_door', methods=['POST'])
def trigger_door():
    """Recebe o comando do Bot do Discord para abrir a porta."""
    data = request.get_json()
    
    # Verifica uma chave secreta simples (definida no .env)
    secret = os.environ.get('OP_SECRET', 'senha_padrao_segura')
    
    if not data or data.get('secret') != secret:
        return jsonify({'status': 'error', 'message': 'Não autorizado'}), 403

    # Registra o comando
    door_open_command['pending'] = True
    door_open_command['timestamp'] = time.time()
    
    logger.info("Comando de abertura remota recebido via API")
    return jsonify({'status': 'success', 'message': 'Comando registrado'})

@main.route('/api/check_door_command', methods=['GET'])
def check_door_command():
    """Endpoint consultado pelo ESP32 para saber se deve abrir a porta."""
    timeout = 10 # O comando expira em 10 segundos se o ESP32 não buscar
    is_pending = door_open_command['pending']
    last_time = door_open_command['timestamp']
    
    should_open = is_pending and (time.time() - last_time < timeout)
    
    if should_open:
        door_open_command['pending'] = False # Reseta o comando
        logger.info("ESP32 consultou e recebeu comando de abertura")
        return jsonify({'open': True})
    
    return jsonify({'open': False})

# --- Endpoints Existentes ---

@main.route('/api/rfid_log', methods=['POST'])
def rfid_log():
    data = request.get_json()
    
    if not data or 'uid' not in data or not data['uid'].strip():
        return jsonify({'status': 'error', 'message': 'UID inválido'}), 400

    uid = data['uid'].strip()
    
    try:
        username, status = process_rfid_access(uid)
        
        new_log = AccessLog(tag_uid=uid, username=username, status=status)
        db.session.add(new_log)
        db.session.commit()
        
        try:
            import threading
            thread = threading.Thread(target=send_discord_webhook, args=(uid, username, status))
            thread.daemon = True
            thread.start()
        except Exception as e:
            logger.error(f"Erro thread webhook: {e}")
        
        logger.info(f"Acesso processado: {uid} - {status}")
        return jsonify({'status': 'success', 'access_status': status}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro processar log: {e}")
        return jsonify({'status': 'error'}), 500

@main.route('/api/get_logs')
@login_required
def get_logs():
    try:
        logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(5).all()
        log_list = [{
            'username': log.username,
            'tag_uid': log.tag_uid,
            'timestamp': log.timestamp.astimezone().strftime('%d/%m/%Y %H:%M:%S'),
            'status': log.status
        } for log in logs]
        return jsonify(log_list)
    except Exception as e:
        return jsonify({'error': 'Erro ao carregar logs'}), 500

@main.route('/')
@main.route('/index')
@login_required
def index():
    try:
        tags = RfidTag.query.all()
        return render_template('index.html', title='Página Inicial', tags=tags)
    except Exception:
        return render_template('index.html', title='Página Inicial', tags=[])

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
        try:
            existing_tag = RfidTag.query.filter_by(tag_uid=form.tag_uid.data).first()
            if existing_tag:
                flash('Tag já registrada!', 'warning')
            else:
                tag = RfidTag(tag_uid=form.tag_uid.data, username=form.username.data)
                db.session.add(tag)
                db.session.commit()
                flash('Tag registrada com sucesso!', 'success')
                return redirect(url_for('main.index'))
        except Exception:
            db.session.rollback()
            flash('Erro ao registrar tag.', 'danger')
    return render_template('register_tag.html', title='Registrar Tag', form=form)

@main.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})