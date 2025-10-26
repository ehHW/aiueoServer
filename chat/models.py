from django.db import models
from django.db.models import Q, F, CheckConstraint, UniqueConstraint, Index
from django.core.validators import MaxLengthValidator
from django.forms import ValidationError
from django.db.models import Func, IntegerField, Value
from user.models import User


# ---------- 1. 好友请求 ----------
class FriendRequest(models.Model):
    PENDING, ACCEPTED, DECLINED = "pending", "accepted", "declined"
    STATUS_CHOICES = [(PENDING, "Pending"), (ACCEPTED, "Accepted"), (DECLINED, "Declined")]

    # 谁发起的（真正的发起人）
    from_user_id = models.PositiveIntegerField(db_index=True, default=0)

    # 谁接收的
    to_user_id = models.PositiveIntegerField(db_index=True, default=1)

    # 用于保证关系唯一性（不区分方向）
    lesser_id = models.PositiveIntegerField(editable=False, db_index=True)
    greater_id = models.PositiveIntegerField(editable=False, db_index=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            CheckConstraint(check=~Q(from_user_id=F("to_user_id")), name="chat_no_self_request"),
            UniqueConstraint(fields=["lesser_id", "greater_id"], name="chat_uniq_friend_pair"),
        ]
        indexes = [
            Index(fields=["from_user_id", "status"], name="chat_from_status_idx"),
            Index(fields=["to_user_id", "status"], name="chat_to_status_idx"),
        ]

    def clean(self):
        # 保证关系唯一性字段始终有序
        self.lesser_id, self.greater_id = sorted([self.from_user_id, self.to_user_id])

    def save(self, *, force_insert=False, force_update=False, **kwargs):
        self.clean()
        super().save(force_insert=force_insert, force_update=force_update, **kwargs)

    @property
    def from_user(self):
        return User.objects.filter(pk=self.from_user_id).first()

    @property
    def to_user(self):
        return User.objects.filter(pk=self.to_user_id).first()


# ---------- 2. 会话 ----------
class JSONLength(Func):
    function = "JSON_LENGTH"
    output_field = IntegerField()


class Conversation(models.Model):
    PRIVATE, GROUP = "private", "group"
    TYPE_CHOICES = [(PRIVATE, "Private"), (GROUP, "Group")]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255, blank=True)
    private_members = models.JSONField(
        null=True, blank=True, db_index=True,
        help_text="私聊时存放 [user_id1, user_id2]，升序"
    )
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name="created_conversations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=(
                    Q(type=Value('group')) |
                    (Q(type=Value('private')) & Q(private_members__length=2))
                ),
                name='private_must_have_two_members',
            ),
            UniqueConstraint(
                fields=['private_members'],
                condition=Q(type=Value('private')),
                name='uniq_private_conv',
            ),
        ]

    def clean(self):
        super().clean()
        if self.type == self.PRIVATE:
            if not isinstance(self.private_members, list) or len(self.private_members) != 2:
                raise ValidationError("私聊必须设置且仅设置两名成员")
            self.private_members = sorted(self.private_members)

    def save(self, *, force_insert=False, force_update=False, **kwargs):
        # FIX: 保证 bulk_create 也排序
        if self.type == self.PRIVATE:
            self.private_members = sorted(self.private_members)
        super().save(force_insert=force_insert, force_update=force_update, **kwargs)


# ---------- 3. 会话参与者 ----------
class ConversationParticipant(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="conversation_participants"
    )
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        related_name="participants"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    read_up_to_msg_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "conversation"], name="uniq_user_conv")
        ]


# ---------- 4. 消息 ----------
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    content = models.TextField(validators=[MaxLengthValidator(20000)])
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_recalled = models.BooleanField(default=False)
    recalled_at = models.DateTimeField(null=True, blank=True)
    recall_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    parent_message = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="replies"
    )

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            Index(fields=["conversation", "timestamp"]),
            # FIX: 倒序拉最新消息可复用，或单独再建
        ]


# ---------- 5. 私聊已读表 ----------
class MessageRead(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="read_messages"
    )
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE,
        related_name="read_by"
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "message"], name="uniq_read")
        ]