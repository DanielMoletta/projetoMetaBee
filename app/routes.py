from flask import render_template, flash, redirect, url_for, Blueprint, request, jsonify
from app import db
from app.forms import LoginForm, TagRegistrationForm
from app.models import User, RfidTag, AccessLog
from flask_login import current_user, login_user, logout_user, login_required
import requests
import os
from datetime import datetime
import logging

main = Blueprint('main', __name__)

# Configuração de logging
logger = logging.getLogger(__name__)

# --- Constantes ---
DISCORD_COLORS = {
    "Acesso Negado": 15158332,  # Vermelho
    "Acesso Garantido": 3066993  # Verde
}

DISCORD_TITLES = {
    "Acesso Negado": "❌ Acesso Negado: Tag Desconhecida",
    "Acesso Garantido": "✅ Acesso Garantido: {}"
}

# --- Funções Auxiliares Otimizadas ---

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
        # Usando timeout para evitar bloqueio prolongado
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

# --- Endpoints da API Otimizados ---

@main.route('/api/rfid_log', methods=['POST'])
def rfid_log():
    """Recebe o UID do ESP32, determina o status, registra e notifica."""
    data = request.get_json()
    
    # Validação mais robusta
    if not data or 'uid' not in data or not data['uid'].strip():
        return jsonify({
            'status': 'error', 
            'message': 'UID não fornecido ou inválido'
        }), 400

    uid = data['uid'].strip()
    
    try:
        # Processa o acesso
        username, status = process_rfid_access(uid)
        
        # Cria e salva o registro de log
        new_log = AccessLog(tag_uid=uid, username=username, status=status)
        db.session.add(new_log)
        db.session.commit()
        
        # Envia notificação de forma não-bloqueante
        try:
            import threading
            thread = threading.Thread(
                target=send_discord_webhook, 
                args=(uid, username, status)
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            logger.error(f"Erro ao iniciar thread do webhook: {e}")
        
        logger.info(f"Acesso processado: {uid} - {status}")
        return jsonify({
            'status': 'success', 
            'message': 'Log recebido',
            'access_status': status
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar RFID log: {e}")
        return jsonify({
            'status': 'error', 
            'message': 'Erro interno do servidor'
        }), 500

@main.route('/api/get_logs')
@login_required
def get_logs():
    """Fornece os 5 logs mais recentes de forma otimizada."""
    try:
        logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(5).all()
        
        log_list = [
            {
                'username': log.username,
                'tag_uid': log.tag_uid,
                'timestamp': log.timestamp.astimezone().strftime('%d/%m/%Y %H:%M:%S'),
                'status': log.status
            }
            for log in logs
        ]
        
        return jsonify(log_list)
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs: {e}")
        return jsonify({'error': 'Erro ao carregar logs'}), 500

# --- Rotas da Interface Web Otimizadas ---

@main.route('/')
@main.route('/index')
@login_required
def index():
    """Página inicial com lista de tags."""
    try:
        tags = RfidTag.query.all()
        return render_template('index.html', title='Página Inicial', tags=tags)
    except Exception as e:
        logger.error(f"Erro ao carregar página inicial: {e}")
        flash('Erro ao carregar a página.', 'danger')
        return render_template('index.html', title='Página Inicial', tags=[])

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login com tratamento de erro melhorado."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            
            if user is None or not user.check_password(form.password.data):
                flash('Usuário ou senha inválidos', 'danger')
                return redirect(url_for('main.login'))
            
            login_user(user, remember=form.remember_me.data)
            
            # Log de login bem-sucedido
            logger.info(f"Login bem-sucedido: {user.username}")
            return redirect(url_for('main.index'))
            
        except Exception as e:
            logger.error(f"Erro durante login: {e}")
            flash('Erro interno durante o login.', 'danger')
    
    return render_template('login.html', title='Entrar', form=form)

@main.route('/logout')
def logout():
    """Rota de logout com logging."""
    if current_user.is_authenticated:
        logger.info(f"Logout: {current_user.username}")
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/register_tag', methods=['GET', 'POST'])
@login_required
def register_tag():
    """Rota de registro de tag com validação melhorada."""
    form = TagRegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Verifica se a tag já existe
            existing_tag = RfidTag.query.filter_by(tag_uid=form.tag_uid.data).first()
            if existing_tag:
                flash('Esta tag RFID já está registrada!', 'warning')
                return render_template('register_tag.html', title='Registrar Tag RFID', form=form)
            
            # Cria nova tag
            tag = RfidTag(tag_uid=form.tag_uid.data, username=form.username.data)
            db.session.add(tag)
            db.session.commit()
            
            logger.info(f"Tag registrada: {form.tag_uid.data} para {form.username.data}")
            flash('Nova tag RFID registrada com sucesso!', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar tag: {e}")
            flash('Erro ao registrar a tag RFID.', 'danger')
    
    return render_template('register_tag.html', title='Registrar Tag RFID', form=form)

# --- Rota de Health Check ---
@main.route('/health')
def health_check():
    """Rota simples para verificar se a aplicação está rodando."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})