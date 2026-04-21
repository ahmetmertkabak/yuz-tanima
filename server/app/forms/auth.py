"""Authentication-related WTForms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp


class LoginForm(FlaskForm):
    username = StringField(
        "Kullanıcı Adı",
        validators=[DataRequired(), Length(min=2, max=64)],
        render_kw={"autocomplete": "username", "autofocus": True},
    )
    password = PasswordField(
        "Şifre",
        validators=[DataRequired(), Length(min=8, max=128)],
        render_kw={"autocomplete": "current-password"},
    )
    remember_me = BooleanField("Beni Hatırla")
    submit = SubmitField("Giriş Yap")


class TwoFactorForm(FlaskForm):
    """Second step of login for users with TOTP enabled."""

    code = StringField(
        "Doğrulama Kodu",
        validators=[
            DataRequired(),
            Length(min=6, max=6),
            Regexp(r"^\d{6}$", message="6 haneli rakam girin"),
        ],
        render_kw={
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "autofocus": True,
            "placeholder": "123456"},
    )
    submit = SubmitField("Doğrula")


class TwoFactorSetupForm(FlaskForm):
    """Confirm 2FA setup by entering a code from the authenticator app."""

    code = StringField(
        "Doğrulama Kodu",
        validators=[
            DataRequired(),
            Length(min=6, max=6),
            Regexp(r"^\d{6}$", message="6 haneli rakam girin")],
        render_kw={"autocomplete": "one-time-code", "inputmode": "numeric"},
    )
    submit = SubmitField("2FA'yı Etkinleştir")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Mevcut Şifre",
        validators=[DataRequired()],
        render_kw={"autocomplete": "current-password"},
    )
    new_password = PasswordField(
        "Yeni Şifre",
        validators=[DataRequired(), Length(min=8, max=128)],
        render_kw={"autocomplete": "new-password"},
    )
    confirm_password = PasswordField(
        "Yeni Şifre (Tekrar)",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Şifreler eşleşmiyor")],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("Şifreyi Değiştir")


class PasswordResetRequestForm(FlaskForm):
    email = StringField(
        "E-posta",
        validators=[DataRequired(), Email(), Length(max=120)],
        render_kw={"autocomplete": "email", "autofocus": True},
    )
    submit = SubmitField("Sıfırlama Bağlantısı Gönder")


class PasswordResetForm(FlaskForm):
    new_password = PasswordField(
        "Yeni Şifre",
        validators=[DataRequired(), Length(min=8, max=128)],
        render_kw={"autocomplete": "new-password", "autofocus": True},
    )
    confirm_password = PasswordField(
        "Yeni Şifre (Tekrar)",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Şifreler eşleşmiyor"),
        ],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("Şifreyi Sıfırla")