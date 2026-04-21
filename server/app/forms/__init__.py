"""WTForms form classes."""
from app.forms.auth import (
    ChangePasswordForm,
    LoginForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    TwoFactorForm,
    TwoFactorSetupForm,
)
from app.forms.device import DeviceCreateForm, DeviceEditForm
from app.forms.person import (
    PersonBulkActionForm,
    PersonBulkImportForm,
    PersonForm,
)
from app.forms.school import SchoolCreateForm, SchoolEditForm

__all__ = [
    "LoginForm",
    "TwoFactorForm",
    "TwoFactorSetupForm",
    "ChangePasswordForm",
    "PasswordResetRequestForm",
    "PasswordResetForm",
    "SchoolCreateForm",
    "SchoolEditForm",
    "DeviceCreateForm",
    "DeviceEditForm",
    "PersonForm",
    "PersonBulkImportForm",
    "PersonBulkActionForm"]