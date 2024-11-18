from init_base import *
from users.models import *


@transaction.atomic
def create_menus():
    for i in range(10):
        Menu.objects.create(
            is_frame=faker.boolean(),
            sort=faker.random_int(min=1, max=10),
            name=faker.unique.word(),
            icon=faker.image_url(),
            path=faker.uri_path(),
            component=faker.word(),
            code=faker.unique.word(),
            pid=random.choice(Menu.objects.filter(id__gt=1)) if len(Menu.objects.filter(id__gt=1)) > 3 else None,
        )


@transaction.atomic
def create_btns():
    for i in range(20):
        Btn.objects.create(
            type=random.choice([1, 2]),
            name=faker.unique.word(),
            perm=faker.unique.word(),
            code=faker.unique.word(),
            pid=random.choice(Btn.objects.filter(id__gt=1)).id if len(Btn.objects.filter(id__gt=1)) > 3 else None,
        )


@transaction.atomic
def create_perms():
    for i in range(5):
        Perm.objects.create(
            name=faker.unique.word(),
            code=faker.unique.word(),
            method=faker.unique.word(),
            menus=random.choice(Menu.objects.filter(id__gt=1)),
            pid=random.choice(Perm.objects.filter(id__gt=1)) if len(Perm.objects.filter(id__gt=1)) > 3 else None,
        )


@transaction.atomic
def create_roles():
    for i in range(10):
        # 创建角色
        role = Role.objects.create(name=faker.unique.word(), code=faker.unique.word())

        # 随机选择权限
        perms = list(Perm.objects.all())
        if perms:
            selected_perms = random.sample(perms, random.randint(1, min(5, len(perms))))
            role.perms.add(*selected_perms)

        # 随机选择按钮
        btns = list(Btn.objects.all())
        if btns:
            selected_btns = random.sample(btns, random.randint(1, min(5, len(btns))))
            role.btns.add(*selected_btns)

        # 随机选择菜单
        menus = list(Menu.objects.all())
        if menus:
            selected_menus = random.sample(menus, random.randint(1, min(5, len(menus))))
            role.menus.add(*selected_menus)


@transaction.atomic
def create_depts():
    for i in range(10):
        Dept.objects.create(
            name=faker.unique.word(),
            code=faker.unique.word(),
            type=random.choice(["company", "department"]),
            pid=random.choice(Dept.objects.filter(id__gt=1)) if len(Dept.objects.filter(id__gt=1)) > 3 else None,
        )


# @transaction.atomic
def create_users():
    existing_codes = set()  # 用于存储已存在的代码
    existing_usernames = set()  # 用于存储已存在的用户名
    for i in range(10000):
        # 随机选择一个非删除的部门
        dept = Dept.objects.filter(del_flag=False).order_by("?").first()  # 随机获取一个部门

        # 确保生成唯一的代码
        code = faker.word()  # 使用faker生成的单词
        while code in existing_codes or User.objects.filter(code=code).exists():  # 检查数据库中是否已存在该代码
            code = faker.word()  # 重新生成代码
        existing_codes.add(code)

        # 确保生成唯一的用户名
        username = faker.unique.user_name()
        while username in existing_usernames or User.objects.filter(username=username).exists():  # 检查数据库中是否已存在该用户名
            username = faker.unique.user_name()  # 重新生成用户名
        existing_usernames.add(username)

        # 创建用户
        user = User.objects.create(
            username=username,
            nick_name=faker.first_name(),
            code=code,
            email=faker.unique.email(),
            phone=faker.phone_number()[:11],
            gender=random.choice([1, 2]),
            avatar=faker.image_url(),  # 使用正确的字段名
            dept=dept,
            create_by=User.objects.first(),  # 随机获取一个操作人
            update_by=User.objects.first(),  # 随机获取一个操作人
        )

        # 可选：分配角色
        # 假设您有角色的列表，可以随机选择一个角色
        roles = list(Role.objects.all())
        if roles:  # 确保角色列表不为空
            selected_roles = random.sample(roles, random.randint(1, min(3, len(roles))))  # 随机选择 1 到 3 个角色
            user.roles.add(*selected_roles)  # 添加角色到用户


@transaction.atomic
def init_super_user():
    admin_user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "nick_name": "管理员",
            "phone": faker.phone_number()[:11],
            "gender": 1,
            "is_superuser": True,
            "is_staff": True,
            "code": faker.unique.word(),
        },
    )
    # if created:
    #     print("Super admin user created.")
    # else:
    #     print("Super admin user already exists.")
    #
    # # 分配超级管理员角色
    # admin_user.roles.add(Role.objects.get(name="admin"))
    admin_user.set_password("123456")
    admin_user.save()
    # print(admin_user.roles.values("perms__method").distinct())


if __name__ == "__main__":
    # create_menus()
    # create_btns()
    # create_perms()
    # create_roles()
    # create_depts()
    init_super_user()
    # create_users()
