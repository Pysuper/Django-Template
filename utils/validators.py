import re
from datetime import datetime
from typing import Any, List, Optional, Pattern, Union

from django.core.exceptions import ValidationError
from django.core.validators import (
    EmailValidator,
    MaxLengthValidator,
    MinLengthValidator,
    RegexValidator,
    URLValidator,
)
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext as _


@deconstructible
class PasswordValidator:
    """密码验证器：验证密码的复杂度"""

    def __init__(
        self,
        min_length: int = 8,
        max_length: int = 32,
        special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?/",
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
        forbidden_words: Optional[List[str]] = None,
        max_repeating_chars: int = 3,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.special_chars = special_chars
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
        self.forbidden_words = forbidden_words or []
        self.max_repeating_chars = max_repeating_chars

    def validate(self, password: str, user: Optional[Any] = None) -> None:
        if len(password) < self.min_length:
            raise ValidationError(
                _("密码长度不能小于%(min_length)d个字符"),
                code="password_too_short",
                params={"min_length": self.min_length},
            )

        if len(password) > self.max_length:
            raise ValidationError(
                _("密码长度不能大于%(max_length)d个字符"),
                code="password_too_long",
                params={"max_length": self.max_length},
            )

        if self.require_uppercase and not any(char.isupper() for char in password):
            raise ValidationError(_("密码必须包含至少一个大写字母"), code="password_no_upper")

        if self.require_lowercase and not any(char.islower() for char in password):
            raise ValidationError(_("密码必须包含至少一个小写字母"), code="password_no_lower")

        if self.require_digits and not any(char.isdigit() for char in password):
            raise ValidationError(_("密码必须包含至少一个数字"), code="password_no_digit")

        if self.require_special and not any(char in self.special_chars for char in password):
            raise ValidationError(_("密码必须包含至少一个特殊字符"), code="password_no_special")

        # 检查禁用词
        password_lower = password.lower()
        for word in self.forbidden_words:
            if word.lower() in password_lower:
                raise ValidationError(_("密码不能包含禁用词: %(word)s"), code="password_forbidden_word", params={"word": word})

        # 检查重复字符
        for i in range(len(password) - self.max_repeating_chars + 1):
            if len(set(password[i:i + self.max_repeating_chars])) == 1:
                raise ValidationError(
                    _("密码不能包含%(count)d个或以上的连续重复字符"),
                    code="password_repeating_chars",
                    params={"count": self.max_repeating_chars},
                )

        # 检查键盘序列
        keyboard_sequences = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890"]
        for seq in keyboard_sequences:
            if any(seq[i:i + 4].lower() in password_lower for i in range(len(seq) - 3)):
                raise ValidationError(_("密码不能包含键盘序列"), code="password_keyboard_sequence")

    def get_help_text(self) -> str:
        help_texts = [f"密码长度必须在{self.min_length}-{self.max_length}个字符之间"]
        if self.require_uppercase:
            help_texts.append("必须包含至少一个大写字母")
        if self.require_lowercase:
            help_texts.append("必须包含至少一个小写字母")
        if self.require_digits:
            help_texts.append("必须包含至少一个数字")
        if self.require_special:
            help_texts.append(f"必须包含至少一个特殊字符({self.special_chars})")
        if self.forbidden_words:
            help_texts.append(f"不能包含以下词语: {', '.join(self.forbidden_words)}")
        help_texts.append(f"不能包含{self.max_repeating_chars}个或以上的连续重复字符")
        help_texts.append("不能包含键盘序列")
        return "，".join(help_texts) + "。"


@deconstructible
class ChinesePhoneNumberValidator:
    """中国手机号码验证器"""

    def __init__(self, allow_virtual: bool = False):
        self.allow_virtual = allow_virtual
        self.regex = r"^1[3-9]\d{9}$"
        self.virtual_prefixes = ["165", "166", "167", "170", "171", "172", "173", "174", "175", "176", "177", "178", "179"]
        self.validator = RegexValidator(regex=self.regex, message=_("请输入有效的中国手机号码"), code="invalid_phone_number")

    def __call__(self, value: str) -> None:
        self.validator(value)
        if not self.allow_virtual and value[:3] in self.virtual_prefixes:
            raise ValidationError(_("不支持虚拟运营商号码"), code="virtual_phone_number")


@deconstructible
class ChineseIDCardValidator:
    """中国身份证号码验证器"""

    def __init__(self, min_age: Optional[int] = None, max_age: Optional[int] = None):
        self.regex = r"^\d{17}[\dXx]$"
        self.validator = RegexValidator(regex=self.regex, message=_("请输入有效的身份证号码"), code="invalid_id_card")
        self.min_age = min_age
        self.max_age = max_age

    def __call__(self, value: str) -> None:
        self.validator(value)
        self._validate_checksum(value)
        self._validate_birthday(value)
        if self.min_age or self.max_age:
            self._validate_age(value)

    def _validate_checksum(self, value: str) -> None:
        """验证身份证校验码"""
        factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        checksum_map = "10X98765432"

        # 计算校验码
        checksum = sum(int(value[i]) * factors[i] for i in range(17))
        expected = checksum_map[checksum % 11]

        if value[-1].upper() != expected:
            raise ValidationError(_("身份证号码校验码错误"), code="invalid_id_card_checksum")

    def _validate_birthday(self, value: str) -> None:
        """验证出生日期"""
        try:
            year = int(value[6:10])
            month = int(value[10:12])
            day = int(value[12:14])
            birthday = datetime(year, month, day)

            # 检查是否超过当前日期
            if birthday > datetime.now():
                raise ValidationError(_("出生日期不能超过当前日期"), code="future_birthday")
        except ValueError:
            raise ValidationError(_("身份证号码中的出生日期无效"), code="invalid_birthday")

    def _validate_age(self, value: str) -> None:
        """验证年龄范围"""
        birth_date = datetime(
            year=int(value[6:10]),
            month=int(value[10:12]),
            day=int(value[12:14]),
        )
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        if self.min_age and age < self.min_age:
            raise ValidationError(
                _("年龄不能小于%(min_age)d岁"),
                code="age_too_young",
                params={"min_age": self.min_age},
            )

        if self.max_age and age > self.max_age:
            raise ValidationError(
                _("年龄不能大于%(max_age)d岁"),
                code="age_too_old",
                params={"max_age": self.max_age},
            )


@deconstructible
class UsernameValidator:
    """用户名验证器"""

    def __init__(
        self,
        min_length: int = 3,
        max_length: int = 32,
        allowed_chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.",
        regex: Optional[str] = None,
        forbidden_words: Optional[List[str]] = None,
        check_confusables: bool = True,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.allowed_chars = allowed_chars
        self.regex = regex or f"^[{re.escape(allowed_chars)}]+$"
        self.forbidden_words = forbidden_words or []
        self.check_confusables = check_confusables

        self.validators = [
            MinLengthValidator(min_length),
            MaxLengthValidator(max_length),
            RegexValidator(
                regex=self.regex,
                message=_("用户名只能包含字母、数字和特殊字符(_-.)"),
                code="invalid_username",
            ),
        ]

    def __call__(self, value: str) -> None:
        # 运行所有验证器
        for validator in self.validators:
            validator(value)

        # 检查禁用词
        value_lower = value.lower()
        for word in self.forbidden_words:
            if word.lower() in value_lower:
                raise ValidationError(
                    _("用户名不能包含禁用词: %(word)s"),
                    code="username_forbidden_word",
                    params={"word": word},
                )

        # 检查易混淆字符
        if self.check_confusables:
            confusables = [
                ("0", "o"),
                ("1", "l", "i"),
                ("2", "z"),
                ("5", "s"),
                ("6", "b"),
                ("8", "b"),
                ("rn", "m"),
                ("cl", "d"),
            ]
            for group in confusables:
                count = sum(value_lower.count(char) for char in group)
                if count >= 2:
                    raise ValidationError(
                        _("用户名包含易混淆字符组合: %(chars)s"),
                        code="username_confusable",
                        params={"chars": ", ".join(group)},
                    )


@deconstructible
class BusinessLicenseValidator:
    """统一社会信用代码验证器"""

    def __init__(self):
        self.regex = r"^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$"
        self.validator = RegexValidator(
            regex=self.regex,
            message=_("请输入有效的统一社会信用代码"),
            code="invalid_business_license",
        )
        self.weight_factors = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
        self.base_codes = "0123456789ABCDEFGHJKLMNPQRTUWXY"

    def __call__(self, value: str) -> None:
        self.validator(value)
        self._validate_checksum(value)

    def _validate_checksum(self, value: str) -> None:
        """验证校验码"""
        try:
            # 计算加权因子
            total = sum(
                self.weight_factors[i] * self.base_codes.index(value[i].upper())
                for i in range(17)
            )
            checksum = 31 - (total % 31)
            if checksum == 31:
                checksum = 0

            # 验证校验码
            if self.base_codes[checksum] != value[17].upper():
                raise ValidationError(_("统一社会信用代码校验码错误"), code="invalid_license_checksum")
        except ValueError:
            raise ValidationError(_("统一社会信用代码格式错误"), code="invalid_license_format")


@deconstructible
class BankCardValidator:
    """银行卡号验证器"""

    def __init__(self, allowed_types: Optional[List[str]] = None):
        self.regex = r"^\d{16,19}$"
        self.validator = RegexValidator(
            regex=self.regex,
            message=_("请输入有效的银行卡号"),
            code="invalid_bank_card",
        )
        self.allowed_types = allowed_types

    def __call__(self, value: str) -> None:
        self.validator(value)
        self._validate_luhn(value)
        if self.allowed_types:
            self._validate_card_type(value)

    def _validate_luhn(self, value: str) -> None:
        """验证Luhn算法"""
        digits = [int(d) for d in value]
        checksum = 0
        odd = True

        for digit in digits[-2::-1]:
            if odd:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
            odd = not odd

        if (checksum * 9) % 10 != int(value[-1]):
            raise ValidationError(_("银行卡号校验失败"), code="invalid_card_checksum")

    def _validate_card_type(self, value: str) -> None:
        """验证卡片类型"""
        card_types = {
            "visa": ["4"],
            "mastercard": ["51", "52", "53", "54", "55"],
            "amex": ["34", "37"],
            "unionpay": ["62"],
        }

        detected_type = None
        for card_type, prefixes in card_types.items():
            if any(value.startswith(prefix) for prefix in prefixes):
                detected_type = card_type
                break

        if detected_type not in self.allowed_types:
            raise ValidationError(
                _("不支持的银行卡类型，仅支持: %(types)s"),
                code="unsupported_card_type",
                params={"types": ", ".join(self.allowed_types)},
            )


# 常用验证器实例
password_validator = PasswordValidator(
    forbidden_words=["password", "admin", "123456", "qwerty"],
    max_repeating_chars=3,
)
phone_number_validator = ChinesePhoneNumberValidator(allow_virtual=False)
id_card_validator = ChineseIDCardValidator(min_age=18, max_age=100)
username_validator = UsernameValidator(
    forbidden_words=["admin", "root", "system", "test"],
    check_confusables=True,
)
business_license_validator = BusinessLicenseValidator()
bank_card_validator = BankCardValidator(allowed_types=["visa", "mastercard", "unionpay"])
email_validator = EmailValidator(message=_("请输入有效的电子邮件地址"))
url_validator = URLValidator(message=_("请输入有效的URL地址"))
