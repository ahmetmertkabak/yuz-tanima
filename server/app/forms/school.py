"""School management forms (super-admin)."""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateTimeLocalField,
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    Regexp,
)

from app.models import SubscriptionStatus


SUBDOMAIN_REGEX = r"^[a-z][a-z0-9\-]{1,48}[a-z0-9]$"


class SchoolCreateForm(FlaskForm):
    name = StringField(
        "Okul Adı",
        validators=[DataRequired(), Length(min=3, max=200)],
    )
    subdomain = StringField(
        "Subdomain",
        validators=[
            DataRequired(),
            Length(min=3, max=50),
            Regexp(
                SUBDOMAIN_REGEX,
                message="Sadece küçük harf, rakam ve tire. Harf ile başlamalı.",
            )],
        render_kw={"placeholder": "ali-pasa-lisesi"},
    )
    contact_name = StringField("Yetkili Adı", validators=[Optional(), Length(max=120)])
    contact_email = StringField(
        "Yetkili E-posta",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    phone = StringField("Telefon", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Adres", validators=[Optional(), Length(max=1000)])

    max_devices = IntegerField(
        "Maksimum Cihaz",
        validators=[DataRequired(), NumberRange(min=1, max=50)],
        default=1,
    )
    max_persons = IntegerField(
        "Maksimum Kişi",
        validators=[DataRequired(), NumberRange(min=1, max=10_000)],
        default=500,
    )

    # Initial admin user
    admin_username = StringField(
        "Admin Kullanıcı Adı",
        validators=[DataRequired(), Length(min=3, max=64)],
    )
    admin_email = StringField(
        "Admin E-posta",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    admin_full_name = StringField(
        "Admin Ad Soyad", validators=[Optional(), Length(max=120)]
    )
    admin_password = StringField(
        "Admin İlk Şifre",
        validators=[DataRequired(), Length(min=8, max=128)],
        description="Admin bu şifreyle giriş yapar ve sonra değiştirir.",
    )

    trial_days = IntegerField(
        "Deneme Süresi (gün)",
        validators=[NumberRange(min=0, max=365)],
        default=30,
    )

    submit = SubmitField("Okulu Oluştur")


class SchoolEditForm(FlaskForm):
    name = StringField(
        "Okul Adı", validators=[DataRequired(), Length(min=3, max=200)]
    )
    contact_name = StringField("Yetkili Adı", validators=[Optional(), Length(max=120)])
    contact_email = StringField(
        "Yetkili E-posta", validators=[Optional(), Email(), Length(max=120)]
    )
    phone = StringField("Telefon", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Adres", validators=[Optional(), Length(max=1000)])

    max_devices = IntegerField(
        "Maksimum Cihaz", validators=[DataRequired(), NumberRange(min=1, max=50)]
    )
    max_persons = IntegerField(
        "Maksimum Kişi",
        validators=[DataRequired(), NumberRange(min=1, max=10_000)],
    )

    timezone = StringField(
        "Zaman Dilimi",
        validators=[DataRequired(), Length(max=50)],
        default="Europe/Istanbul",
    )
    recognition_tolerance = FloatField(
        "Yüz Tanıma Toleransı",
        validators=[DataRequired(), NumberRange(min=0.3, max=0.9)],
        description="Düşük = daha katı (önerilen 0.55)",
    )

    subscription_status = SelectField(
        "Abonelik Durumu",
        choices=[(s.value, s.value.title()) for s in SubscriptionStatus],
        validators=[DataRequired()],
    )
    subscription_expires_at = DateTimeLocalField(
        "Abonelik Bitiş Tarihi",
        format="%Y-%m-%dT%H:%M",
        validators=[Optional()],
    )

    is_active = BooleanField("Aktif", default=True)

    submit = SubmitField("Güncelle")