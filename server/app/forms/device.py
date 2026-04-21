"""Device management forms (super-admin)."""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models import DeviceDirectionMode


DIRECTION_CHOICES = [
    (DeviceDirectionMode.BIDIRECTIONAL.value, "Çift Yönlü (Giriş + Çıkış)"),
    (DeviceDirectionMode.IN_ONLY.value, "Sadece Giriş"),
    (DeviceDirectionMode.OUT_ONLY.value, "Sadece Çıkış")]


class DeviceCreateForm(FlaskForm):
    school_id = SelectField(
        "Okul",
        coerce=int,
        validators=[DataRequired()],
    )
    device_name = StringField(
        "Cihaz Adı",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Ana Giriş"},
    )
    location = StringField(
        "Konum",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "A Blok Zemin Kat"},
    )
    description = TextAreaField(
        "Açıklama", validators=[Optional(), Length(max=1000)]
    )
    direction_mode = SelectField(
        "Yön Modu",
        choices=DIRECTION_CHOICES,
        default=DeviceDirectionMode.BIDIRECTIONAL.value,
    )
    turnstile_pulse_ms = IntegerField(
        "Turnike Pulse Süresi (ms)",
        validators=[DataRequired(), NumberRange(min=50, max=5000)],
        default=500,
    )
    recognition_tolerance = FloatField(
        "Yüz Tanıma Toleransı (okul varsayılanını kullanmak için boş bırakın)",
        validators=[Optional(), NumberRange(min=0.3, max=0.9)],
    )

    submit = SubmitField("Cihazı Oluştur")


class DeviceEditForm(FlaskForm):
    device_name = StringField(
        "Cihaz Adı",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    location = StringField("Konum", validators=[Optional(), Length(max=200)])
    description = TextAreaField(
        "Açıklama", validators=[Optional(), Length(max=1000)]
    )
    direction_mode = SelectField("Yön Modu", choices=DIRECTION_CHOICES)
    turnstile_pulse_ms = IntegerField(
        "Turnike Pulse Süresi (ms)",
        validators=[DataRequired(), NumberRange(min=50, max=5000)],
    )
    recognition_tolerance = FloatField(
        "Yüz Tanıma Toleransı",
        validators=[Optional(), NumberRange(min=0.3, max=0.9)],
    )
    is_active = BooleanField("Aktif")
    submit = SubmitField("Güncelle")