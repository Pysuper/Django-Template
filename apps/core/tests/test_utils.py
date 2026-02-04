"""
Utils Tests / 工具函数测试

测试apps/core中的工具函数
"""

from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

from apps.core.utils import (
    PathAndRename,
    validate_file_size,
    get_client_ip,
    mask_sensitive_data,
)


class PathAndRenameTest(TestCase):
    """PathAndRename类测试"""

    def setUp(self):
        """设置测试"""
        self.path_and_rename = PathAndRename('uploads')

    def test_rename_with_valid_file(self):
        """测试重命名有效文件"""
        file = SimpleUploadedFile("test.jpg", b"file content")
        new_path = self.path_and_rename(file, 'test.jpg')

        self.assertIn('uploads/', new_path)
        self.assertTrue(new_path.endswith('.jpg'))

    def test_different_extensions(self):
        """测试不同文件扩展名"""
        extensions = ['jpg', 'png', 'pdf', 'docx']
        for ext in extensions:
            file = SimpleUploadedFile(f"test.{ext}", b"file content")
            new_path = self.path_and_rename(file, f'test.{ext}')
            self.assertTrue(new_path.endswith(f'.{ext}'))


class ValidateFileSizeTest(TestCase):
    """文件大小验证测试"""

    def test_valid_size(self):
        """测试有效文件大小"""
        file = SimpleUploadedFile("test.jpg", b"x" * (1024 * 1024))  # 1MB
        result = validate_file_size(file, max_size=5)
        self.assertTrue(result)

    def test_invalid_size(self):
        """测试无效文件大小"""
        file = SimpleUploadedFile("test.jpg", b"x" * (6 * 1024 * 1024))  # 6MB
        result = validate_file_size(file, max_size=5)
        self.assertFalse(result)


class GetClientIPTest(TestCase):
    """获取客户端IP测试"""

    def setUp(self):
        """设置测试"""
        self.factory = RequestFactory()

    def test_ip_from_remote_addr(self):
        """测试从REMOTE_ADDR获取IP"""
        request = self.factory.get('/', REMOTE_ADDR='192.168.1.1')
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    def test_ip_from_x_forwarded_for(self):
        """测试从X-Forwarded-For获取IP"""
        request = self.factory.get(
            '/',
            HTTP_X_FORWARDED_FOR='203.0.113.1, 192.168.1.1'
        )
        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')

    def test_no_ip(self):
        """测试没有IP的情况"""
        request = self.factory.get('/')
        ip = get_client_ip(request)
        self.assertIsNone(ip)


class MaskSensitiveDataTest(TestCase):
    """敏感数据脱敏测试"""

    def test_mask_email(self):
        """测试邮箱脱敏"""
        email = "user@example.com"
        masked = mask_sensitive_data(email, data_type='email')
        self.assertIn('***', masked)
        self.assertIn('@example.com', masked)

    def test_mask_phone(self):
        """测试手机号脱敏"""
        phone = "13800138000"
        masked = mask_sensitive_data(phone, data_type='phone')
        self.assertIn('***', masked)
        self.assertTrue(masked.endswith('8000'))

    def test_mask_id_card(self):
        """测试身份证号脱敏"""
        id_card = "110101199001011234"
        masked = mask_sensitive_data(id_card, data_type='id_card')
        self.assertIn('***', masked)

    def test_mask_bank_card(self):
        """测试银行卡号脱敏"""
        bank_card = "6222021234567890123"
        masked = mask_sensitive_data(bank_card, data_type='bank_card')
        self.assertIn('***', masked)

    def test_unknown_type(self):
        """测试未知类型"""
        data = "some data"
        masked = mask_sensitive_data(data, data_type='unknown')
        self.assertEqual(masked, '***')
