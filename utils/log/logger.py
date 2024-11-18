import logging
import os
import time
import traceback
from functools import wraps
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# 创建日志目录
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 配置日志格式
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s")

# 创建logger实例
logger = logging.getLogger("django")
logger.setLevel(logging.INFO)

# # 添加控制台处理器
# # 创建一个 StreamHandler 实例，默认情况下，它将日志消息输出到控制台（标准输出 sys.stdout）
# console_handler = logging.StreamHandler()
# # 为 console_handler 设置一个格式化器 formatter。格式化器定义了日志消息的输出格式，比如时间戳、日志级别、消息内容等
# console_handler.setFormatter(formatter)
# # 将 console_handler 添加到 logger 中。这意味着 logger 记录的日志消息将通过 console_handler 输出到控制台
# logger.addHandler(console_handler)

# 添加按大小轮转的文件处理器
file_handler = RotatingFileHandler(  # 这是一个文件处理器，它会在日志文件达到指定大小时进行轮转
    os.path.join(LOG_DIR, "django.log"),
    maxBytes=10 * 1024 * 1024,  # 设置日志文件的最大大小为 10 MB, 当日志文件达到这个大小时，会创建一个新的日志文件
    backupCount=5,  # 保留最多 5 个旧的日志文件。超过这个数量的旧日志文件将被删除。
    encoding="utf-8",  # 使用 UTF-8 编码写入日志文件
)
file_handler.setFormatter(formatter)  # 设置日志格式
logger.addHandler(file_handler)  # 将处理器添加到 logger，使其生效。


# # 添加按时间轮转的文件处理器
# time_handler = TimedRotatingFileHandler(  # 这是一个文件处理器，它会在指定的时间间隔后进行轮转
#     os.path.join(LOG_DIR, "django.log"),
#     when="midnight",  # when="midnight": 每天午夜进行日志文件轮转
#     interval=1,  # 轮转间隔为 1 天。
#     backupCount=30,  #  保留最多 30 个旧的日志文件。超过这个数量的旧日志文件将被删除。
#     encoding="utf-8",  # 使用 UTF-8 编码写入日志文件
# )
# time_handler.setFormatter(formatter)
# logger.addHandler(time_handler)


# 性能监控装饰器 - 用于记录函数执行时间
def log_time(func):
    """
    装饰器函数,用于记录被装饰函数的执行时间
    :param func: 被装饰的函数
    :return: wrapper函数
    """

    @wraps(func)  # 保留原函数的元数据
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 执行原函数
        end_time = time.time()  # 记录结束时间
        duration = (end_time - start_time) * 1000  # 计算执行时间(毫秒)
        logger.info(f"函数 {func.__name__} 执行时间: {duration:.2f}ms")
        return result

    return wrapper


# 异常捕获装饰器 - 用于记录函数执行过程中的异常信息
def log_exception(func):
    """
    装饰器函数,用于捕获并记录被装饰函数执行时的异常
    :param func: 被装饰的函数
    :return: wrapper函数
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录详细的异常信息
            logger.error(f"函数 {func.__name__} 执行异常: {str(e)}")
            logger.error(f"异常堆栈信息: {traceback.format_exc()}")
            raise  # 重新抛出异常,保持原有的异常处理流程

    return wrapper


# 代码块执行时间上下文管理器
class LogTimeContext:
    """
    上下文管理器类,用于记录代码块的执行时间
    使用方法:
    with LogTimeContext("业务操作名称"):
        # 需要计时的代码块
    """

    def __init__(self, name):
        """
        初始化上下文管理器
        :param name: 代码块名称标识
        """
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        logger.info(f"{self.name} 执行时间: {duration:.2f}ms")


# 批量日志处理器
class BatchLogger:
    """
    批量日志处理类,用于批量记录日志,避免频繁IO操作
    当日志数量达到阈值时自动写入,也可手动调用flush方法写入
    """

    def __init__(self, max_batch=100):
        """
        初始化批量日志处理器
        :param max_batch: 最大批处理数量,默认100条
        """
        self.logs = []  # 日志缓存列表
        self.max_batch = max_batch  # 最大批处理数量

    def add(self, message, level=logging.INFO):
        """
        添加日志消息
        :param message: 日志消息内容
        :param level: 日志级别,默认INFO
        """
        self.logs.append((level, message))
        if len(self.logs) >= self.max_batch:
            self.flush()

    def flush(self):
        """
        将缓存的日志写入到日志文件
        """
        for level, message in self.logs:
            logger.log(level, message)
        self.logs.clear()  # 清空缓存
