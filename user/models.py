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


# 好友表
class FriendRequest(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (DECLINED, 'Declined'),
    ]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests', db_index=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests', db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['sender', 'receiver']

    def save(self, *args, **kwargs):
        if self.sender_id > self.receiver_id:
            self.sender, self.receiver = self.receiver, self.sender
        super().save(*args, **kwargs)


# 会话表
class Conversation(models.Model):
    PRIVATE = 'private'
    GROUP = 'group'
    TYPE_CHOICES = [
        (PRIVATE, 'Private'),
        (GROUP, 'Group'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255, null=True, blank=True)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)


# 会话参与者表
class ConversationParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_participants', db_index=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants', db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'conversation']


# 消息表
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', db_index=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
        ]


# 消息已读表
class MessageRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_messages')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'message']


