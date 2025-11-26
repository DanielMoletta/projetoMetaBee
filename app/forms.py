from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from app.models import RfidTag

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class TagRegistrationForm(FlaskForm):
    tag_uid = StringField('UID da Tag RFID', validators=[DataRequired()])
    username = StringField('Nome do Usuário', validators=[DataRequired()])
    picture = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Cadastrar Tag')

    def validate_tag_uid(self, tag_uid):
        tag = RfidTag.query.filter_by(tag_uid=tag_uid.data).first()
        if tag is not None:
            raise ValidationError('Este UID de tag já foi registrado.')

    def validate_username(self, username):
        tag = RfidTag.query.filter_by(username=username.data).first()
        if tag is not None:
            raise ValidationError('Este nome para tag já está em uso.')