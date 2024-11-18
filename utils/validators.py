from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class SpecialCharacterValidator:
    """
    自定义密码验证器, 验证密码是否包含特殊字符
    """

    def validate(self, password, user=None):
        if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for char in password):
            raise ValidationError(
                _("This password must contain at least one special character."),
                code="password_no_special_character",
            )

    def get_help_text(self):
        return _("Your password must contain at least one special character.")
