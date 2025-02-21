import io
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage, default_storage
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from utils.log.logger import logger


class ImageProcessor:
    """图片处理器"""

    def __init__(
        self,
        storage: Optional[Storage] = None,
        quality: int = 85,
        max_size: Optional[Tuple[int, int]] = None,
        allowed_formats: Optional[List[str]] = None,
    ):
        self.storage = storage or default_storage
        self.quality = quality
        self.max_size = max_size
        self.allowed_formats = allowed_formats or ["JPEG", "PNG", "GIF", "BMP", "WEBP"]

    def resize_image(
        self,
        image_path: str,
        size: Tuple[int, int],
        save_path: Optional[str] = None,
        keep_ratio: bool = True,
        quality: Optional[int] = None,
    ) -> str:
        """
        调整图片大小
        :param image_path: 图片路径
        :param size: 目标尺寸
        :param save_path: 保存路径
        :param keep_ratio: 是否保持宽高比
        :param quality: 图片质量
        :return: 保存路径
        """
        try:
            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

                # 调整大小
                if keep_ratio:
                    image.thumbnail(size, Image.Resampling.LANCZOS)
                else:
                    image = image.resize(size, Image.Resampling.LANCZOS)

                # 生成保存路径
                if not save_path:
                    directory = os.path.dirname(image_path)
                    filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_resized.jpg"
                    save_path = os.path.join(directory, filename)

                # 保存图片
                return self._save_image(image, save_path, quality=quality)

        except Exception as e:
            logger.error(f"调整图片大小失败: {str(e)}")
            raise

    def crop_image(
        self,
        image_path: str,
        box: Tuple[int, int, int, int],
        save_path: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """
        裁剪图片
        :param image_path: 图片路径
        :param box: 裁剪区域 (left, top, right, bottom)
        :param save_path: 保存路径
        :param quality: 图片质量
        :return: 保存路径
        """
        try:
            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

                # 裁剪图片
                image = image.crop(box)

                # 生成保存路径
                if not save_path:
                    directory = os.path.dirname(image_path)
                    filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_cropped.jpg"
                    save_path = os.path.join(directory, filename)

                # 保存图片
                return self._save_image(image, save_path, quality=quality)

        except Exception as e:
            logger.error(f"裁剪图片失败: {str(e)}")
            raise

    def add_watermark(
        self,
        image_path: str,
        watermark: Union[str, Image.Image],
        position: Tuple[int, int] = (0, 0),
        opacity: float = 0.5,
        save_path: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """
        添加水印
        :param image_path: 图片路径
        :param watermark: 水印图片路径或图片对象
        :param position: 水印位置
        :param opacity: 水印透明度
        :param save_path: 保存路径
        :param quality: 图片质量
        :return: 保存路径
        """
        try:
            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

            # 打开水印图片
            if isinstance(watermark, str):
                with self.storage.open(watermark) as f:
                    watermark = Image.open(f)
                    watermark = watermark.convert("RGBA")
            else:
                watermark = watermark.copy()

            # 调整水印透明度
            if opacity < 1:
                watermark.putalpha(int(opacity * 255))

            # 创建新图层
            layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            layer.paste(watermark, position)

            # 合并图层
            image = Image.alpha_composite(image.convert("RGBA"), layer)
            image = image.convert("RGB")

            # 生成保存路径
            if not save_path:
                directory = os.path.dirname(image_path)
                filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_watermarked.jpg"
                save_path = os.path.join(directory, filename)

            # 保存图片
            return self._save_image(image, save_path, quality=quality)

        except Exception as e:
            logger.error(f"添加水印失败: {str(e)}")
            raise

    def add_text_watermark(
        self,
        image_path: str,
        text: str,
        position: Tuple[int, int] = (0, 0),
        font_path: Optional[str] = None,
        font_size: int = 36,
        font_color: Tuple[int, int, int] = (255, 255, 255),
        opacity: float = 0.5,
        save_path: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """
        添加文字水印
        :param image_path: 图片路径
        :param text: 水印文字
        :param position: 水印位置
        :param font_path: 字体路径
        :param font_size: 字体大小
        :param font_color: 字体颜色
        :param opacity: 水印透明度
        :param save_path: 保存路径
        :param quality: 图片质量
        :return: 保存路径
        """
        try:
            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

            # 创建字体对象
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()

            # 创建新图层
            layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)

            # 绘制文字
            draw.text(
                position,
                text,
                font=font,
                fill=(*font_color, int(opacity * 255)),
            )

            # 合并图层
            image = Image.alpha_composite(image.convert("RGBA"), layer)
            image = image.convert("RGB")

            # 生成保存路径
            if not save_path:
                directory = os.path.dirname(image_path)
                filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_text.jpg"
                save_path = os.path.join(directory, filename)

            # 保存图片
            return self._save_image(image, save_path, quality=quality)

        except Exception as e:
            logger.error(f"添加文字水印失败: {str(e)}")
            raise

    def compress_image(
        self,
        image_path: str,
        save_path: Optional[str] = None,
        max_size: Optional[int] = None,
        quality: Optional[int] = None,
    ) -> str:
        """
        压缩图片
        :param image_path: 图片路径
        :param save_path: 保存路径
        :param max_size: 最大文件大小（字节）
        :param quality: 图片质量
        :return: 保存路径
        """
        try:
            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

            # 生成保存路径
            if not save_path:
                directory = os.path.dirname(image_path)
                filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_compressed.jpg"
                save_path = os.path.join(directory, filename)

            # 压缩图片
            if max_size:
                # 二分法查找合适的质量值
                min_quality = 1
                max_quality = quality or self.quality
                target_quality = max_quality
                while min_quality <= max_quality:
                    # 尝试当前质量值
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=target_quality)
                    size = buffer.tell()

                    # 判断是否满足大小要求
                    if size <= max_size:
                        if min_quality == max_quality:
                            break
                        min_quality = target_quality + 1
                    else:
                        max_quality = target_quality - 1
                    target_quality = (min_quality + max_quality) // 2

                quality = target_quality

            # 保存图片
            return self._save_image(image, save_path, quality=quality)

        except Exception as e:
            logger.error(f"压缩图片失败: {str(e)}")
            raise

    def convert_format(
        self,
        image_path: str,
        format: str,
        save_path: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """
        转换图片格式
        :param image_path: 图片路径
        :param format: 目标格式
        :param save_path: 保存路径
        :param quality: 图片质量
        :return: 保存路径
        """
        try:
            # 检查格式是否支持
            format = format.upper()
            if format not in self.allowed_formats:
                raise ValueError(f"不支持的图片格式: {format}")

            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

            # 生��保存路径
            if not save_path:
                directory = os.path.dirname(image_path)
                filename = f"{os.path.splitext(os.path.basename(image_path))[0]}.{format.lower()}"
                save_path = os.path.join(directory, filename)

            # 保存图片
            return self._save_image(image, save_path, format=format, quality=quality)

        except Exception as e:
            logger.error(f"转换图片格式失败: {str(e)}")
            raise

    def apply_filter(
        self,
        image_path: str,
        filter_type: str,
        save_path: Optional[str] = None,
        quality: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        应用滤镜
        :param image_path: 图片路径
        :param filter_type: 滤镜类型
        :param save_path: 保存路径
        :param quality: 图片质量
        :param kwargs: 滤镜参数
        :return: 保存路径
        """
        try:
            # 打开图片
            with self.storage.open(image_path) as f:
                image = Image.open(f)
                image = image.convert("RGB")

            # 应用滤镜
            if filter_type == "BLUR":
                image = image.filter(ImageFilter.BLUR)
            elif filter_type == "CONTOUR":
                image = image.filter(ImageFilter.CONTOUR)
            elif filter_type == "EDGE_ENHANCE":
                image = image.filter(ImageFilter.EDGE_ENHANCE)
            elif filter_type == "EMBOSS":
                image = image.filter(ImageFilter.EMBOSS)
            elif filter_type == "SHARPEN":
                image = image.filter(ImageFilter.SHARPEN)
            elif filter_type == "SMOOTH":
                image = image.filter(ImageFilter.SMOOTH)
            elif filter_type == "BRIGHTNESS":
                factor = kwargs.get("factor", 1.0)
                image = ImageEnhance.Brightness(image).enhance(factor)
            elif filter_type == "COLOR":
                factor = kwargs.get("factor", 1.0)
                image = ImageEnhance.Color(image).enhance(factor)
            elif filter_type == "CONTRAST":
                factor = kwargs.get("factor", 1.0)
                image = ImageEnhance.Contrast(image).enhance(factor)
            elif filter_type == "SHARPNESS":
                factor = kwargs.get("factor", 1.0)
                image = ImageEnhance.Sharpness(image).enhance(factor)
            else:
                raise ValueError(f"不支持的滤镜类型: {filter_type}")

            # 生成保存路径
            if not save_path:
                directory = os.path.dirname(image_path)
                filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_{filter_type.lower()}.jpg"
                save_path = os.path.join(directory, filename)

            # 保存图片
            return self._save_image(image, save_path, quality=quality)

        except Exception as e:
            logger.error(f"应用滤镜失败: {str(e)}")
            raise

    def _save_image(
        self,
        image: Image.Image,
        save_path: str,
        format: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> str:
        """
        保存图片
        :param image: 图片对象
        :param save_path: 保存路径
        :param format: 图片格式
        :param quality: 图片质量
        :return: 保存路径
        """
        # 创建临时文件
        buffer = io.BytesIO()
        image.save(
            buffer,
            format=format or "JPEG",
            quality=quality or self.quality,
            optimize=True,
        )
        buffer.seek(0)

        # 保存文件
        return self.storage.save(save_path, File(buffer))


# 创建默认图片处理器实例
image_processor = ImageProcessor()


"""
使用示例：

# 调整图片大小
processor = ImageProcessor()
resized_path = processor.resize_image(
    "uploads/image.jpg",
    size=(800, 600),
    keep_ratio=True
)

# 裁剪图片
cropped_path = processor.crop_image(
    "uploads/image.jpg",
    box=(100, 100, 500, 500)
)

# 添加水印
watermarked_path = processor.add_watermark(
    "uploads/image.jpg",
    watermark="watermark.png",
    position=(50, 50),
    opacity=0.7
)

# 添加文字水印
text_path = processor.add_text_watermark(
    "uploads/image.jpg",
    text="Copyright 2023",
    position=(50, 50),
    font_size=36,
    font_color=(255, 255, 255)
)

# 压缩图片
compressed_path = processor.compress_image(
    "uploads/image.jpg",
    max_size=1024 * 1024  # 1MB
)

# 转换格式
converted_path = processor.convert_format(
    "uploads/image.jpg",
    format="PNG"
)

# 应用滤镜
filtered_path = processor.apply_filter(
    "uploads/image.jpg",
    filter_type="BLUR"
)

# 调整亮度
brightened_path = processor.apply_filter(
    "uploads/image.jpg",
    filter_type="BRIGHTNESS",
    factor=1.5
)

# 配置示例
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
IMAGE_QUALITY = 85
MAX_IMAGE_SIZE = (1920, 1080)
ALLOWED_IMAGE_FORMATS = ["JPEG", "PNG", "GIF", "WEBP"]
""" 