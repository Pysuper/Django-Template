"""
Services Layer:
服务层是应用的核心，负责处理应用的业务逻辑。
可以将复杂的业务逻辑抽象成服务层，并将服务层的接口暴露给控制器层调用。
这样可以降低控制器层的复杂度，提高代码的可维护性。
例如，用户注册、登录等业务逻辑可以抽象成 UserService 类，并提供相应的接口，比如 register() 和 login() 方法。
控制器层只需要调用 UserService 类的 register() 和 login() 方法，并处理相应的业务逻辑即可。
"""


class UserService:
    def register(self, username, password):
        # 实现用户注册的业务逻辑
        # 例如，检查用户名是否已存在，然后将用户信息插入到数据库中
        pass

    def login(self, username, password):
        # 实现用户登录的业务逻辑
        # 例如，检查用户名和密码是否匹配，然后返回用户的相关信息
        pass


# 控制器层调用 UserService 类的 register() 和 login() 方法
user_service = UserService()
user_service.register("test", "123456")
user_service.login("test", "123456")
