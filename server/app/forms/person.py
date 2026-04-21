"""Person (student/teacher/staff) management forms."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    Optional,
    Regexp,
)

from app.models import ConsentStatus, PersonRole


ROLE_CHOICES = [
    (PersonRole.STUDENT.value, "Öğrenci"),
    (PersonRole.TEACHER.value, "Öğretmen"),
    (PersonRole.STAFF.value, "Personel"),
    (PersonRole.MANAGER.value, "Yönetici")]

CONSENT_CHOICES = [
    (ConsentStatus.PENDING.value, "Bekliyor"),
    (ConsentStatus.GRANTED.value, "Verildi"),
    (ConsentStatus.REVOKED.value, "Geri Çekildi")]


class PersonForm(FlaskForm):
    """Create / edit a person."""

    person_no = StringField(
        "No / Sicil",
        validators=[DataRequired(), Length(max=30)],
        render_kw={"placeholder": "örn. 1234 veya STU001"},
    )
    full_name = StringField(
        "Ad Soyad",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    role = SelectField("Rol", choices=ROLE_CHOICES, validators=[DataRequired()])
    class_name = StringField(
        "Sınıf",
        validators=[Optional(), Length(max=30)],
        render_kw={"placeholder": "örn. 9-A"},
    )
    email = StringField("E-posta", validators=[Optional(), Email(), Length(max=120)])
    phone = StringField("Telefon", validators=[Optional(), Length(max=20)])
    parent_name = StringField("Veli Adı", validators=[Optional(), Length(max=120)])
    parent_phone = StringField("Veli Telefonu", validators=[Optional(), Length(max=20)])
    notes = TextAreaField("Notlar", validators=[Optional(), Length(max=2000)])
    is_active = BooleanField("Aktif", default=True)
    access_granted = BooleanField("Erişim İzni", default=True)
    consent_status = SelectField(
        "KVKK Onay Durumu",
        choices=CONSENT_CHOICES,
        default=ConsentStatus.PENDING.value,
    )
    submit = SubmitField("Kaydet")


class PersonBulkImportForm(FlaskForm):
    """Upload an Excel file with person rows."""

    file = FileField(
        "Excel Dosyası",
        validators=[
            FileRequired(message="Bir dosya seçin."),
            FileAllowed(["xlsx", "xls", "csv"], "Sadece Excel veya CSV.")],
    )
    default_role = SelectField(
        "Varsayılan Rol",
        choices=ROLE_CHOICES,
        default=PersonRole.STUDENT.value,
        description="Dosyada role kolonu yoksa bu rol kullanılır.",
    )
    overwrite = BooleanField(
        "Mevcut kayıtları güncelle",
        default=False,
        description="Aynı person_no zaten varsa üzerine yaz.",
    )
    submit = SubmitField("Yükle")


class PersonBulkActionForm(FlaskForm):
    """Hidden form used by the multi-select action bar on the list page."""

    ids = StringField(validators=[DataRequired()])  # comma-separated
    action = StringField(validators=[DataRequired()])
    submit = SubmitField()