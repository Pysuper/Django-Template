import logging
import platform
import os
import ctypes
import time

# 平台判断，定义跨平台的颜色设置函数
if platform.system() == "Windows":

    def set_color_windows(level):
        """Windows 平台下设置控制台输出颜色"""
        color_map = {
            50: 0x004E,  # Critical: Yellow background, red text
            40: 0x000C,  # Error: Red
            30: 0x000E,  # Warning: Yellow
            20: 0x0002,  # Info: Green
            10: 0x0005,  # Debug: Magenta
            0: 0x0007,  # Default: White
        }
        color_code = next((color for lvl, color in color_map.items() if level >= lvl), 0x0007)
        ctypes.windll.kernel32.SetConsoleTextAttribute(ctypes.windll.kernel32.GetStdHandle(-11), color_code)

    def reset_color_windows():
        """重置控制台颜色"""
        ctypes.windll.kernel32.SetConsoleTextAttribute(ctypes.windll.kernel32.GetStdHandle(-11), 0x0007)

    def color_emit_windows(fn):
        """包装 emit 方法，添加颜色支持"""

        def new_emit(*args):
            set_color_windows(args[1].levelno)
            ret = fn(*args)
            reset_color_windows()
            return ret

        return new_emit

    logging.StreamHandler.emit = color_emit_windows(logging.StreamHandler.emit)

else:
    ANSI_COLOR_MAP = {
        50: "\033[91m",  # Critical: 红色
        40: "\033[91m",  # Error: 红色
        30: "\033[93m",  # Warning: 黄色
        20: "\033[92m",  # Info: 绿色
        10: "\033[95m",  # Debug: 紫色
        0: "\033[0m",  # Default: 正常
    }

    def color_emit_ansi(fn):
        """非 Windows 平台使用 ANSI 颜色支持"""

        def new_emit(*args):
            color_code = next((color for lvl, color in ANSI_COLOR_MAP.items() if args[1].levelno >= lvl), "\033[0m")
            args[1].msg = f"{color_code}{args[1].msg}\033[0m"
            return fn(*args)

        return new_emit

    logging.StreamHandler.emit = color_emit_ansi(logging.StreamHandler.emit)


# 定义控制台颜色类
class Color:
    Black = 0
    Red = 1
    Green = 2
    Yellow = 3
    Blue = 4
    Magenta = 5
    Cyan = 6
    White = 7


class Mode:
    Foreground = 30
    Background = 40
    ForegroundBright = 90
    BackgroundBright = 100


def tcolor(color, mode=Mode.Foreground):
    """生成 ANSI 颜色代码"""
    return f"\033[{mode + color}m"


def treset():
    """重置控制台颜色"""
    return "\033[0m"


if __name__ == "__main__":
    os.system("")  # Windows 平台颜色支持

    # 用法示例
    print(tcolor(Color.Red) + "hello" + treset())
    print(tcolor(Color.Green, Mode.Background) + "color" + treset())
    print()

    COLOR_NAMES = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]
    MODE_NAMES = ["Foreground", "Background", "ForegroundBright", "BackgroundBright"]

    fmt = "{:12}" * len(COLOR_NAMES)
    print(" " * 20 + fmt.format(*COLOR_NAMES))

    for mode_name in MODE_NAMES:
        print("{:20}".format(mode_name), end="")
        for color_name in COLOR_NAMES:
            mode = getattr(Mode, mode_name)
            color = getattr(Color, color_name)
            print(tcolor(color, mode) + "HelloColor" + treset(), end=" ")
        print()
