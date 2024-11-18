import os

import django
import random
from faker import Faker

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.users.models import Dept, Role, Menu, User  # 替换为您的应用名和模型

fake = Faker()

def create_random_rbac():
    # 生成部门
    depts = []
    for _ in range(5):  # 假设生成5个部门
        dept = Dept.objects.create(name=fake.unique.company(), dept_sort=fake.random_int(min=1, max=10), sub_count=0)
        depts.append(dept)

    # 生成角色
    roles = []
    for _ in range(10):  # 假设生成10个角色
        role = Role.objects.create(
            name=fake.unique.job(), data_scope=fake.word(), level=fake.random_int(min=1, max=5)
        )  # 假设角色级别在1到5之间
        role.depts.set(random.sample(depts, random.randint(1, len(depts))))  # 随机关联部门
        roles.append(role)

    # 生成菜单
    menus = []
    for _ in range(1, 101):
        menu = Menu.objects.create(
            title=fake.unique.word(),
            name=fake.unique.word(),
            component=fake.word(),
            menu_sort=fake.random_int(min=1, max=10),
            icon=fake.image_url(),
            path=fake.uri_path(),
            i_frame=fake.boolean(),
            cache=fake.boolean(),
            hidden=fake.boolean(),
            permission=fake.word(),
            sub_count=0,
        )
        menus.append(menu)

    # 关联角色和菜单
    for role in roles:
        role.menus.set(random.sample(menus, random.randint(1, len(menus))))  # 随机关联菜单

    # 创建用户数据
    users = []
    for i in range(1, 101):
        # 这里要先用create创建用户，后面再设置密码
        user = User.objects.create(
            username=fake.unique.user_name(),
            nick_name=fake.first_name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:11],
            gender=fake.random_element(elements=(1, 2)),
            avatar_name=fake.image_url(),
            avatar_path=fake.image_url(),
            depression=fake.random_number(digits=3),
            anxiety=fake.random_number(digits=3),
            bipolar_disorder=fake.random_number(digits=3),
            personality=fake.words(nb=5),
            depression_ai=fake.random_number(digits=3),
            personality_ai=fake.random_number(digits=3),
        )
        user.set_password("123456")  # 设置默认密码
        user.save()

        print(user.username, user.check_password("123456"))  # 验证密码

        # 关联角色和部门
        user.roles.set(random.sample(roles, random.randint(1, len(roles))))  # 随机关联角色
        user.dept = Dept.objects.order_by("?").first()  # 随机选择一个部门
        user.save()

    # # 为角色关联菜单（多对多）
    # for role in roles:
    #     role.menus.set(fake.random_elements(elements=menus, unique=True, length=fake.random_int(min=1, max=3)))

def change_password():
    # 随机修改用户的密码
    users = User.objects.all()
    for user in users:
        user.set_password("123456")  # 重置为默认密码
        user.save()

if __name__ == '__main__':
    change_password()
