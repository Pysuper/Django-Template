# 取消外键关联
set foreign_key_checks = 0;

# 清空表
truncate users_user;

# 使用外键关联
set foreign_key_checks = 1;

# 设置自增ID从1开始
ALTER TABLE users_user AUTO_INCREMENT = 1;
