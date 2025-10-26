from django.db import models


class CaiDan2(models.Model):
    auth_id = models.AutoField(primary_key=True)
    icon = models.CharField(max_length=200, blank=True, default='icon-home')
    auth_name = models.CharField(max_length=20, default='')
    path = models.CharField(max_length=200, blank=True, default='')
    type = models.IntegerField(default=1)
    auth_pid = models.IntegerField(default=1)
    auth_pname = models.CharField(max_length=200, blank=True, default='')
    keep_alive = models.IntegerField(default=1)
    component = models.CharField(max_length=200, blank=True, default='')
    sort = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'caidan2'


class CaiDan(models.Model):
    auth_id = models.AutoField(primary_key=True)
    icon = models.CharField(max_length=200, blank=True, default='')
    auth_name = models.CharField(max_length=20, default='')
    path = models.CharField(max_length=200, blank=True, default='')
    type = models.IntegerField(default=1)
    auth_pid = models.IntegerField(default=0)
    auth_pname = models.CharField(max_length=200, blank=True, default='')
    keep_alive = models.IntegerField(default=1)
    component = models.CharField(max_length=200, blank=True, default='')
    sort = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'caidan'


class Permission2(models.Model):
    permission2_id = models.AutoField(primary_key=True)
    permission2_name = models.CharField(max_length=20, default='未命名权限')
    caidan2 = models.ForeignKey(
        'CaiDan2',
        on_delete=models.CASCADE,
        related_name='permissions',
    )

    class Meta:
        db_table = 'permission2'


class Permission(models.Model):
    permission_id = models.AutoField(primary_key=True)
    permission_name = models.CharField(max_length=20, default='未命名权限')
    permission2 = models.ManyToManyField(Permission2, related_name='permissions')
    class Meta:
        db_table = 'permission'


class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=20, default='普通用户')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    role_desc = models.TextField(default='')
    # 一个角色可拥有多个权限
    permission = models.ManyToManyField(Permission, related_name='roles')
    permission2 = models.ManyToManyField(Permission2, related_name='roles')
    class Meta:
        db_table = 'role'


class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=20)
    password = models.CharField(max_length=20)
    mobile = models.CharField(max_length=11, unique=True, default='00000000000')
    avatar = models.ImageField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state = models.IntegerField(default=1)
    role = models.ForeignKey(Role, on_delete=models.SET_DEFAULT, default=5)

    class Meta:
        db_table = 'user'

