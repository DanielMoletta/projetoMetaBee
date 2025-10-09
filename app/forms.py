from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from app.models import RfidTag

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

# O RegistrationForm foi removido e substituído por este novo formulário.
class TagRegistrationForm(FlaskForm):
    tag_uid = StringField('UID da Tag RFID', validators=[DataRequired()])
    username = StringField('Nome Associado à Tag', validators=[DataRequired()])
    submit = SubmitField('Registrar Tag')

    def validate_tag_uid(self, tag_uid):
        tag = RfidTag.query.filter_by(tag_uid=tag_uid.data).first()
        if tag is not None:
            raise ValidationError('Este UID de tag já foi registrado.')

    def validate_username(self, username):
        tag = RfidTag.query.filter_by(username=username.data).first()
        if tag is not None:
            raise ValidationError('Este nome para tag já está em uso.')
