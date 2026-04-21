"""WTForms form classes."""
from app.forms.auth import (
    ChangePasswordForm,
    LoginForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    TwoFactorForm,
    TwoFactorSetupForm,
)
from app.forms.school import SchoolCreateForm, SchoolEditForm
from app.forms.device import DeviceCreateForm, DeviceEditForm

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
    "DeviceEditForm"]