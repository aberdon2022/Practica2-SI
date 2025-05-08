from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, ValidationError, EqualTo
from extensions import db
import sqlalchemy as sa
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        user = db.session.scalar(
            sa.select(User).where(User.username == self.username.data)
        )
        if user is None or not user.check_password(self.password.data):
            self.username.errors.append('Nombre de usuario o contraseña incorrectos.')
            return False
        return True

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(
            sa.select(User).where(User.username == username.data)
        )
        if user:
            self.username.errors.append('El nombre de usuario ya existe.')
            return False
        return True
