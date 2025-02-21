import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from utils.log.logger import logger


class EmailTemplate:
    """邮件模板"""

    def __init__(self, template_name: str, context: Optional[Dict[str, Any]] = None):
        self.template_name = template_name
        self.context = context or {}

    def render(self) -> tuple:
        """
        渲染模板
        :return: (HTML内容, 纯文本内容)
        """
        try:
            html_content = render_to_string(self.template_name, self.context)
            text_content = strip_tags(html_content)
            return html_content, text_content
        except Exception as e:
            logger.error(f"渲染邮件模板失败: {str(e)}")
            raise


class EmailSender:
    """邮件发送器"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: int = 30,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        self.host = host or settings.EMAIL_HOST
        self.port = port or settings.EMAIL_PORT
        self.username = username or settings.EMAIL_HOST_USER
        self.password = password or settings.EMAIL_HOST_PASSWORD
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.from_email = from_email or settings.DEFAULT_FROM_EMAIL
        self.from_name = from_name
        self._connection = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self) -> None:
        """打开连接"""
        if self._connection is None:
            self._connection = get_connection(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
                use_ssl=self.use_ssl,
                timeout=self.timeout,
            )
            self._connection.open()

    def close(self) -> None:
        """关闭连接"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _create_message(
        self,
        subject: str,
        body: str,
        to: Union[str, List[str]],
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Union[str, tuple]]] = None,
        html: bool = False,
    ) -> EmailMessage:
        """
        创建邮件消息
        :param subject: 主题
        :param body: 内容
        :param to: 收件人
        :param cc: 抄送
        :param bcc: 密送
        :param reply_to: 回复地址
        :param attachments: 附件列表
        :param html: 是否为HTML格式
        :return: 邮件消息对象
        """
        if isinstance(to, str):
            to = [to]
        if isinstance(cc, str):
            cc = [cc]
        if isinstance(bcc, str):
            bcc = [bcc]
        if isinstance(reply_to, str):
            reply_to = [reply_to]

        # 创建邮件
        if html:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(body),
                from_email=formataddr((self.from_name, self.from_email)) if self.from_name else self.from_email,
                to=to,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                connection=self._connection,
            )
            msg.attach_alternative(body, "text/html")
        else:
            msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=formataddr((self.from_name, self.from_email)) if self.from_name else self.from_email,
                to=to,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                connection=self._connection,
            )

        # 添加附件
        if attachments:
            for attachment in attachments:
                if isinstance(attachment, str):
                    # 文件路径
                    path = Path(attachment)
                    with open(path, "rb") as f:
                        content = f.read()
                        msg.attach(path.name, content, self._get_mimetype(path.suffix))
                else:
                    # (文件名, 内容, MIME类型)
                    msg.attach(*attachment)

        return msg

    def _get_mimetype(self, suffix: str) -> str:
        """
        获取MIME类型
        :param suffix: 文件后缀
        :return: MIME类型
        """
        mimetypes = {
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
        }
        return mimetypes.get(suffix.lower(), "application/octet-stream")

    def send_mail(
        self,
        subject: str,
        body: str,
        to: Union[str, List[str]],
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Union[str, tuple]]] = None,
        html: bool = False,
        fail_silently: bool = False,
    ) -> bool:
        """
        发送邮件
        :param subject: 主题
        :param body: 内容
        :param to: 收件人
        :param cc: 抄送
        :param bcc: 密送
        :param reply_to: 回复地址
        :param attachments: 附件列表
        :param html: 是否为HTML格式
        :param fail_silently: 是否静默失败
        :return: 是否成功
        """
        try:
            msg = self._create_message(
                subject=subject,
                body=body,
                to=to,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                attachments=attachments,
                html=html,
            )
            msg.send(fail_silently=fail_silently)
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            if not fail_silently:
                raise
            return False

    def send_template_mail(
        self,
        template: EmailTemplate,
        subject: str,
        to: Union[str, List[str]],
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Union[str, tuple]]] = None,
        fail_silently: bool = False,
    ) -> bool:
        """
        发送模板邮件
        :param template: 邮件模板
        :param subject: 主题
        :param to: 收件人
        :param cc: 抄送
        :param bcc: 密送
        :param reply_to: 回复地址
        :param attachments: 附件列表
        :param fail_silently: 是否静默失败
        :return: 是否成功
        """
        try:
            html_content, text_content = template.render()
            return self.send_mail(
                subject=subject,
                body=html_content,
                to=to,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                attachments=attachments,
                html=True,
                fail_silently=fail_silently,
            )
        except Exception as e:
            logger.error(f"发送模板邮件失败: {str(e)}")
            if not fail_silently:
                raise
            return False


class SMTPEmailSender:
    """SMTP邮件发送器"""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: int = 30,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.from_email = from_email
        self.from_name = from_name
        self._server = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def connect(self) -> None:
        """连接SMTP服务器"""
        try:
            if self.use_ssl:
                self._server = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                )
            else:
                self._server = smtplib.SMTP(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                )
                if self.use_tls:
                    self._server.starttls()

            self._server.login(self.username, self.password)
        except Exception as e:
            logger.error(f"连接SMTP服务器失败: {str(e)}")
            raise

    def quit(self) -> None:
        """断开连接"""
        if self._server is not None:
            try:
                self._server.quit()
            except Exception as e:
                logger.error(f"断开SMTP连接失败: {str(e)}")
            finally:
                self._server = None

    def send_mail(
        self,
        subject: str,
        body: str,
        to: Union[str, List[str]],
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Union[str, tuple]]] = None,
        html: bool = False,
        images: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        发送邮件
        :param subject: 主题
        :param body: 内容
        :param to: 收件人
        :param cc: 抄送
        :param bcc: 密送
        :param reply_to: 回复地址
        :param attachments: 附件列表
        :param html: 是否为HTML格式
        :param images: 内嵌图片
        :return: 是否成功
        """
        try:
            if isinstance(to, str):
                to = [to]
            if isinstance(cc, str):
                cc = [cc]
            if isinstance(bcc, str):
                bcc = [bcc]

            # 创建邮件
            msg = MIMEMultipart("related" if images else "mixed")
            msg["Subject"] = subject
            msg["From"] = formataddr((self.from_name, self.from_email)) if self.from_name else self.from_email
            msg["To"] = ", ".join(to)
            if cc:
                msg["Cc"] = ", ".join(cc)
            if reply_to:
                msg["Reply-To"] = ", ".join(reply_to) if isinstance(reply_to, list) else reply_to
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid()

            # 添加正文
            if html:
                msg_alt = MIMEMultipart("alternative")
                msg_alt.attach(MIMEText(strip_tags(body), "plain", "utf-8"))
                msg_alt.attach(MIMEText(body, "html", "utf-8"))
                msg.attach(msg_alt)
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))

            # 添加内嵌图片
            if images:
                for cid, image_path in images.items():
                    with open(image_path, "rb") as f:
                        img = MIMEImage(f.read())
                        img.add_header("Content-ID", f"<{cid}>")
                        img.add_header("Content-Disposition", "inline", filename=os.path.basename(image_path))
                        msg.attach(img)

            # 添加附件
            if attachments:
                for attachment in attachments:
                    if isinstance(attachment, str):
                        # 文件路径
                        path = Path(attachment)
                        with open(path, "rb") as f:
                            part = MIMEApplication(f.read())
                            part.add_header(
                                "Content-Disposition",
                                "attachment",
                                filename=path.name,
                            )
                            msg.attach(part)
                    else:
                        # (文件名, 内容, MIME类型)
                        filename, content, mimetype = attachment
                        part = MIMEApplication(content)
                        part.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=filename,
                        )
                        part.add_header("Content-Type", mimetype)
                        msg.attach(part)

            # 发送邮件
            recipients = to + (cc or []) + (bcc or [])
            self._server.send_message(msg, self.from_email, recipients)
            return True

        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            raise


# 创建默认邮件发送器
email_sender = EmailSender()


"""
使用示例：

# 基本用法
email_sender = EmailSender()
email_sender.send_mail(
    subject="测试邮件",
    body="这是一封测试邮件",
    to="user@example.com",
    cc=["cc1@example.com", "cc2@example.com"],
    attachments=["/path/to/file.pdf"],
)

# 使用模板
template = EmailTemplate(
    "email/welcome.html",
    {"username": "张三", "site_name": "我的网站"}
)
email_sender.send_template_mail(
    template=template,
    subject="欢迎注册",
    to="user@example.com",
)

# 使用SMTP发送器
with SMTPEmailSender(
    host="smtp.example.com",
    port=587,
    username="sender@example.com",
    password="password",
) as sender:
    sender.send_mail(
        subject="测试邮件",
        body="<h1>这是一封HTML邮件</h1>",
        to="user@example.com",
        html=True,
        images={"logo": "/path/to/logo.png"},
    )

# 配置示例
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = "sender@example.com"
EMAIL_HOST_PASSWORD = "password"
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = "sender@example.com"
"""
