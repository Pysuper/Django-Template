import os
import time
from logging.handlers import TimedRotatingFileHandler


# 自定义日志处理器
class CoreLogFileHandler(TimedRotatingFileHandler):
    """
    CustomTimedRotatingFileHandler
    自定义日志处理器，解决多进程环境下日志写入的冲突问题
    """

    def __init__(self, filename, when="midnight", interval=1, backupCount=20, encoding="utf-8"):
        super().__init__(filename, when=when, interval=interval, backupCount=backupCount, encoding=encoding)

    @property
    def dfn(self):
        """获取当前日志文件的名称"""
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                addend = 3600 if dstNow else -3600
                timeTuple = time.localtime(t + addend)
        return self.rotation_filename(self.baseFilename + "." + time.strftime(self.suffix, timeTuple))

    def shouldRollover(self, record):
        """
        判断是否应该执行日志滚动操作：
        1. 如果存档文件已存在，则执行滚动操作
        2. 当前时间达到滚动时间点时执行滚动操作
        """
        dfn = self.dfn
        t = int(time.time())
        return t >= self.rolloverAt or os.path.exists(dfn)

    def doRollover(self):
        """
        执行日志滚动操作：
        1. 关闭当前日志文件句柄并打开新文件
        2. 处理备份日志文件数
        3. 更新下一次的滚动时间点
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # 获取存档日志文件的名称
        dfn = self.dfn

        # 处理存档文件已存在的情况
        if not os.path.exists(dfn):
            self.rotate(self.baseFilename, dfn)

        # 控制备份日志文件数
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

        # 打开新日志文件
        if not self.delay:
            self.stream = self._open()

        # 更新下一次的滚动时间点
        currentTime = int(time.time())
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt += self.interval

        # 处理夏令时变化
        if (self.when == "MIDNIGHT" or self.when.startswith("W")) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            dstNow = time.localtime(currentTime)[-1]
            if dstNow != dstAtRollover:
                addend = -3600 if not dstNow else 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt
