import random

from sql.init_base import *
from users.models import Menu, Btn, Perm, Role, Dept, User


def create_menus(n=10):
    for _ in range(n):
        Menu.objects.create(
            is_frame=faker.boolean(),
            sort=random.randint(1, 100),
            name=faker.unique.word(),
            icon=faker.word(),
            path=faker.url(),
            component=faker.word(),
            pid=None,  # 可以根据需要设置父菜单
        )


def create_buttons(n=10):
    for _ in range(n):
        Btn.objects.create(
            name=faker.word(),
            pid=random.randint(1, 10),
            type=random.choice([1, 2]),
            perm=faker.word(),  # 假设父ID在1到10之间
        )


def create_permissions(n=10):
    for _ in range(n):
        Perm.objects.create(
            name=faker.unique.word(),
            method=faker.word(),
            menus=Menu.objects.order_by("?").first(),  # 随机选择一个菜单
            pid=None,  # 可以根据需要设置父权限
        )


def create_roles(n=5):
    for _ in range(n):
        role = Role.objects.create(name=faker.unique.word(), desc=faker.sentence())
        role.perms.set(Perm.objects.order_by("?")[:3])  # 随机选择3个权限
        role.btns.set(Btn.objects.order_by("?")[:3])  # 随机选择3个按钮
        role.menus.set(Menu.objects.order_by("?")[:3])  # 随机选择3个菜单


def create_departments(n=5):
    for _ in range(n):
        Dept.objects.create(
            name=faker.company(),
            type=random.choice(["company", "department"]),
            pid=None,  # 可以根据需要设置上级部门
        )


def create_users(n=2000):
    # for _ in range(n):
    #     user = User.objects.create_user(
    #         username=fake.unique.user_name(),
    #         email=fake.email(),
    #         phone=fake.phone_number(),
    #         gender=random.choice([1, 2]),
    #         nick_name=fake.name(),
    #         position=random.choice(["student", "teacher", "admin"]),
    #         avatar=fake.image_url(),
    #         dept=Dept.objects.order_by("?").first(),  # 随机选择一个部门
    #     )
    #     user.roles.set(Role.objects.order_by("?")[:2])  # 随机选择2个角色
    # 准备数据
    objects = [
        User(
            username=faker.unique.lexify("?????") + " " + faker.unique.lexify("?????"),
            email=faker.email(),
            phone=faker.numerify(text="1#########"),  # 生成13位随机数字电话号码
            gender=random.choice([1, 2]),
            nick_name=faker.unique.lexify("?????") + " " + faker.unique.lexify("?????"),
            position=random.choice(["student", "teacher", "admin"]),
            avatar=faker.image_url(),
            dept=Dept.objects.order_by("?").first(),  # 随机选择一个部门
        )
        for _ in range(n)
    ]

    # 批量插入
    User.objects.bulk_create(objects, batch_size=100)  # 每次插入1000条


if __name__ == "__main__":
    # create_menus()
    # create_buttons()
    # create_permissions()
    # create_roles()
    # create_departments()
    create_users()
    print("随机数据创建完成！")
