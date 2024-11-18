# -*- coding: utf-8 -*-
from typing import Any, Optional

from django.conf import settings

# 从 settings 中获取数据库映射配置
DATABASE_MAPPING = settings.DATABASE_APPS_MAPPING


class DatabaseAppsRouter:
    """
    数据库路由器
    用于处理多数据库的读写分离、关系和迁移操作
    """

    def db_for_read(self, model: Any, **hints) -> Optional[str]:
        """
        处理数据库读操作路由
        :param model: 数据模型
        :param hints: 额外的提示信息
        :return: 数据库别名
        """
        # 根据模型的 app_label 确定读取操作的数据库
        if model._meta.app_label in DATABASE_MAPPING:
            return DATABASE_MAPPING[model._meta.app_label]  # 返回指定数据库
        return None  # 默认返回 None

    def db_for_write(self, model: Any, **hints) -> Optional[str]:
        """
        处理数据库写操作路由
        :param model: 数据模型
        :param hints: 额外的提示信息
        :return: 数据库别名
        """
        # 根据模型的 app_label 确定写入操作的数据库
        if model._meta.app_label in DATABASE_MAPPING:
            return DATABASE_MAPPING[model._meta.app_label]  # 返回指定数据库
        return None  # 默认返回 None

    def allow_relation(self, obj1: Any, obj2: Any, **hints) -> Optional[bool]:
        """
        判断两个对象是否允许建立关系
        :param obj1: 第一个对象
        :param obj2: 第二个对象
        :param hints: 额外的提示信息
        :return: True允许/False禁止/None默认行为
        """
        # 获取两个对象所属的数据库
        db_obj1 = DATABASE_MAPPING.get(obj1._meta.app_label)
        db_obj2 = DATABASE_MAPPING.get(obj2._meta.app_label)

        # if db_obj1 and db_obj2:
        #     return db_obj1 == db_obj2
        # return None

        # 如果两个对象在同一个数据库中，允许关系
        if db_obj1 and db_obj2:
            if db_obj1 == db_obj2:
                return True  # 同一数据库
            else:
                return False  # 不同数据库，禁止关系
        return None  # 默认返回 None

    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints) -> Optional[bool]:
        """
        控制数据库迁移操作
        :param db: 数据库别名
        :param app_label: 应用标签
        :param model_name: 模型名称
        :param hints: 额外的提示信息
        :return: True允许/False禁止/None默认行为
        """
        # 处理特定模型的迁移
        if "model" in hints:
            model = hints["model"]
            if hasattr(model, "_meta"):
                if model._meta.app_label in DATABASE_MAPPING:
                    return db == DATABASE_MAPPING[model._meta.app_label]

        # 处理整个应用的迁移
        if db in DATABASE_MAPPING.values():
            return DATABASE_MAPPING.get(app_label) == db
        elif app_label in DATABASE_MAPPING:
            return False
        return None

    def allow_syncdb(self, db: str, model: Any) -> Optional[bool]:
        """
        控制数据库同步操作(已废弃，仅用于旧版Django)
        :param db: 数据库别名
        :param model: 数据模型
        :return: True允许/False禁止/None默认行为
        """
        if db in DATABASE_MAPPING.values():
            return DATABASE_MAPPING.get(model._meta.app_label) == db
        elif model._meta.app_label in DATABASE_MAPPING:
            return False
        return None

    # # for Django 1.4 - Django 1.6
    # def allow_syncdb(self, db, model):
    #     """Make sure that apps only appear in the related database."""
    #     # 确保应用只在相关数据库中出现
    #     if db in DATABASE_MAPPING.values():
    #         return DATABASE_MAPPING.get(model._meta.app_label) == db  # 检查模型的 app_label 是否与数据库匹配
    #     elif model._meta.app_label in DATABASE_MAPPING:
    #         return False  # 如果模型在数据库映射中，返回 False
    #     return None  # 默认返回 None
    #
    # # Django 1.7 - Django 1.11
    # def allow_migrate(self, db, app_label, model_name=None, **hints):
    #     """控制迁移操作的数据库"""
    #     print(db, app_label, model_name, hints)  # 打印调试信息
    #     # 确保迁移操作只在相关数据库中进行
    #     if db in DATABASE_MAPPING.values():
    #         return DATABASE_MAPPING.get(app_label) == db  # 检查应用标签与数据库是否匹配
    #     elif app_label in DATABASE_MAPPING:
    #         return False  # 如果应用在数据库映射中，返回 False
    #     return None  # 默认返回 None
