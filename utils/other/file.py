import hashlib
import mimetypes
import os
import shutil
import uuid
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage, default_storage
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, StreamingHttpResponse
from django.utils.encoding import escape_uri_path

from utils.log.logger import logger


class FileHandler:
    """文件处理器"""

    def __init__(
        self,
        storage: Optional[Storage] = None,
        base_dir: Optional[str] = None,
        allowed_extensions: Optional[List[str]] = None,
        max_size: Optional[int] = None,
    ):
        self.storage = storage or default_storage
        self.base_dir = base_dir or getattr(settings, "MEDIA_ROOT", "media")
        self.allowed_extensions = allowed_extensions
        self.max_size = max_size or getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)  # 默认10MB

    def save_file(
        self,
        file: Union[File, UploadedFile],
        directory: Optional[str] = None,
        filename: Optional[str] = None,
        overwrite: bool = False,
    ) -> str:
        """
        保存文件
        :param file: 文件对象
        :param directory: 保存目录
        :param filename: 文件名
        :param overwrite: 是否覆盖
        :return: 文件路径
        """
        try:
            # 验证文件
            self._validate_file(file)

            # 生成保存路径
            save_path = self._get_save_path(file, directory, filename)

            # 检查是否存在
            if not overwrite and self.storage.exists(save_path):
                raise FileExistsError(f"文件已存在: {save_path}")

            # 保存文件
            save_path = self.storage.save(save_path, file)
            return save_path

        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        :param file_path: 文件路径
        :return: 是否成功
        """
        try:
            if self.storage.exists(file_path):
                self.storage.delete(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False

    def get_file_url(self, file_path: str) -> str:
        """
        获取文件URL
        :param file_path: 文件路径
        :return: 文件URL
        """
        try:
            return self.storage.url(file_path)
        except Exception as e:
            logger.error(f"获取文件URL失败: {str(e)}")
            raise

    def get_file_info(self, file_path: str) -> Dict:
        """
        获取文件信息
        :param file_path: 文件路径
        :return: 文件信息
        """
        try:
            stat = self.storage.stat(file_path)
            return {
                "name": os.path.basename(file_path),
                "path": file_path,
                "size": stat.st_size,
                "created_time": datetime.fromtimestamp(stat.st_ctime),
                "modified_time": datetime.fromtimestamp(stat.st_mtime),
                "content_type": mimetypes.guess_type(file_path)[0],
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            raise

    def _validate_file(self, file: Union[File, UploadedFile]) -> None:
        """
        验证文件
        :param file: 文件对象
        """
        # 验证文件大小
        if self.max_size and file.size > self.max_size:
            raise ValueError(f"文件大小超过限制: {self.max_size} bytes")

        # 验证文件类型
        if self.allowed_extensions:
            ext = self._get_file_extension(file.name)
            if ext not in self.allowed_extensions:
                raise ValueError(f"不支持的文件类型: {ext}")

    def _get_save_path(
        self,
        file: Union[File, UploadedFile],
        directory: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> str:
        """
        获取保存路径
        :param file: 文件对象
        :param directory: 保存目录
        :param filename: 文件名
        :return: 保存路径
        """
        # 生成文件名
        if not filename:
            ext = self._get_file_extension(file.name)
            filename = f"{uuid.uuid4().hex}{ext}"

        # 生成保存路径
        if directory:
            save_path = os.path.join(directory, filename)
        else:
            date_path = datetime.now().strftime("%Y/%m/%d")
            save_path = os.path.join(self.base_dir, date_path, filename)

        return save_path

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """
        获取文���扩展名
        :param filename: 文件名
        :return: 扩展名
        """
        return os.path.splitext(filename)[1].lower()


class FileDownloader:
    """文件下载器"""

    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or default_storage

    def download_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        as_attachment: bool = True,
        chunk_size: int = 8192,
    ) -> Union[FileResponse, StreamingHttpResponse]:
        """
        下载文件
        :param file_path: 文件路径
        :param filename: 下载文件名
        :param content_type: 内容类型
        :param as_attachment: 是否作为附件下载
        :param chunk_size: 分块大小
        :return: 响应对象
        """
        try:
            # 检查文件是否存在
            if not self.storage.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 获取文件名
            if not filename:
                filename = os.path.basename(file_path)

            # 获取内容类型
            if not content_type:
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

            # 打开文件
            file = self.storage.open(file_path)

            # 创建响应
            response = FileResponse(
                file,
                content_type=content_type,
                as_attachment=as_attachment,
                filename=filename,
            )

            # 设置文件大小
            if hasattr(file, "size"):
                response["Content-Length"] = file.size

            # 设置文件名
            if as_attachment:
                response["Content-Disposition"] = f'attachment; filename="{escape_uri_path(filename)}"'

            return response

        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            raise

    def stream_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        chunk_size: int = 8192,
    ) -> StreamingHttpResponse:
        """
        流式下载文件
        :param file_path: 文件路径
        :param filename: 下载文件名
        :param content_type: 内容类型
        :param chunk_size: 分块大小
        :return: 响应对象
        """
        try:
            # 检查文件是否存在
            if not self.storage.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 获取文件名
            if not filename:
                filename = os.path.basename(file_path)

            # 获取内容类型
            if not content_type:
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

            # 定义文件迭代器
            def file_iterator(file_obj, chunk_size):
                while True:
                    chunk = file_obj.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            # 打开文件
            file = self.storage.open(file_path)

            # 创建响应
            response = StreamingHttpResponse(
                file_iterator(file, chunk_size),
                content_type=content_type,
            )

            # 设置文件大小
            if hasattr(file, "size"):
                response["Content-Length"] = file.size

            # 设置文件名
            response["Content-Disposition"] = f'attachment; filename="{escape_uri_path(filename)}"'

            return response

        except Exception as e:
            logger.error(f"流式下载文件失败: {str(e)}")
            raise


class FileCompressor:
    """文件压缩器"""

    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or default_storage

    def compress_files(
        self,
        files: List[Union[str, Tuple[str, str]]],
        output_path: str,
        compression: int = zipfile.ZIP_DEFLATED,
    ) -> str:
        """
        压缩文件
        :param files: 文件列表，每个元素可以是文件路径或(文件路径, 压缩包内路径)的元组
        :param output_path: 输出路径
        :param compression: 压缩方式
        :return: 压缩文件路径
        """
        try:
            # 创建临时目录
            temp_dir = os.path.join(settings.MEDIA_ROOT, "temp", datetime.now().strftime("%Y%m%d"))
            os.makedirs(temp_dir, exist_ok=True)

            # 创建临时文件
            temp_file = os.path.join(temp_dir, f"{uuid.uuid4().hex}.zip")

            # 创建压缩文件
            with zipfile.ZipFile(temp_file, "w", compression=compression) as zf:
                for file in files:
                    if isinstance(file, tuple):
                        file_path, arc_name = file
                    else:
                        file_path = file
                        arc_name = os.path.basename(file)

                    # 检查文件是否存在
                    if not self.storage.exists(file_path):
                        raise FileNotFoundError(f"文件不存在: {file_path}")

                    # 添加文件到压缩包
                    with self.storage.open(file_path) as f:
                        zf.writestr(arc_name, f.read())

            # 保存压缩文件
            with open(temp_file, "rb") as f:
                save_path = self.storage.save(output_path, File(f))

            # 删除临时文件
            os.remove(temp_file)

            return save_path

        except Exception as e:
            logger.error(f"压缩文件失败: {str(e)}")
            raise

    def extract_files(
        self,
        zip_path: str,
        extract_path: Optional[str] = None,
        members: Optional[List[str]] = None,
    ) -> List[str]:
        """
        解压文件
        :param zip_path: 压缩文件路径
        :param extract_path: 解压路径
        :param members: 要解压的文件列表
        :return: 解压后的文件列表
        """
        try:
            # 检查文件是否存在
            if not self.storage.exists(zip_path):
                raise FileNotFoundError(f"文件不存在: {zip_path}")

            # 创建临时目录
            temp_dir = os.path.join(settings.MEDIA_ROOT, "temp", datetime.now().strftime("%Y%m%d"))
            os.makedirs(temp_dir, exist_ok=True)

            # 创建临时文件
            temp_file = os.path.join(temp_dir, f"{uuid.uuid4().hex}.zip")

            # 复制压缩文件到临时文件
            with self.storage.open(zip_path) as src, open(temp_file, "wb") as dst:
                shutil.copyfileobj(src, dst)

            # 解压文件
            extracted_files = []
            with zipfile.ZipFile(temp_file) as zf:
                # 获取要解压的文件列表
                if members is None:
                    members = zf.namelist()

                # 解���文件
                for member in members:
                    # 生成解压路径
                    if extract_path:
                        save_path = os.path.join(extract_path, member)
                    else:
                        save_path = os.path.join(self.storage.base_location, member)

                    # 创建目录
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)

                    # 解压文件
                    with zf.open(member) as src, open(save_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                    extracted_files.append(save_path)

            # 删除临时文件
            os.remove(temp_file)

            return extracted_files

        except Exception as e:
            logger.error(f"解压文件失败: {str(e)}")
            raise


class FileHasher:
    """文件哈希计算器"""

    def __init__(self, storage: Optional[Storage] = None, chunk_size: int = 8192):
        self.storage = storage or default_storage
        self.chunk_size = chunk_size

    def calculate_hash(self, file_path: str, algorithm: str = "md5") -> str:
        """
        计算文件哈希值
        :param file_path: 文件路径
        :param algorithm: 哈希算法
        :return: 哈希值
        """
        try:
            # 检查文件是否存在
            if not self.storage.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 创建哈希对象
            hasher = hashlib.new(algorithm)

            # 读取文件内容并更新哈希值
            with self.storage.open(file_path) as f:
                for chunk in iter(lambda: f.read(self.chunk_size), b""):
                    hasher.update(chunk)

            return hasher.hexdigest()

        except Exception as e:
            logger.error(f"计算文件哈希值失败: {str(e)}")
            raise


# 创建默认实例
file_handler = FileHandler()
file_downloader = FileDownloader()
file_compressor = FileCompressor()
file_hasher = FileHasher()


"""
使用示例：

# 文件上传
handler = FileHandler(
    allowed_extensions=[".jpg", ".png", ".pdf"],
    max_size=5 * 1024 * 1024  # 5MB
)
file_path = handler.save_file(
    request.FILES["file"],
    directory="uploads",
    filename="example.jpg"
)

# 文件下载
downloader = FileDownloader()
response = downloader.download_file(
    "uploads/example.jpg",
    filename="custom_name.jpg"
)

# 流式下载
response = downloader.stream_file(
    "uploads/large_file.zip",
    chunk_size=8192
)

# 文件��缩
compressor = FileCompressor()
zip_path = compressor.compress_files(
    [
        "uploads/file1.txt",
        ("uploads/file2.jpg", "images/custom_name.jpg")
    ],
    "archives/files.zip"
)

# 文件解压
extracted_files = compressor.extract_files(
    "archives/files.zip",
    extract_path="extracted"
)

# 计算文件哈希值
hasher = FileHasher()
md5_hash = hasher.calculate_hash("uploads/example.jpg", "md5")
sha256_hash = hasher.calculate_hash("uploads/example.jpg", "sha256")

# 配置示例
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_UPLOAD_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"]
"""
