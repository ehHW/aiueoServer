import json
import os
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
import django
from django.forms import ValidationError

from utils.token import decode_refresh_token

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiueoServer.settings')
django.setup()
from .models import Conversation, Message
from user.models import User
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    @staticmethod
    @sync_to_async
    def save_message(conv_id, sender_id, content, parent_id=None):
        conv = Conversation.objects.get(pk=conv_id)
        sender = User.objects.get(pk=sender_id)
        parent = None
        if parent_id:
            parent = Message.objects.filter(pk=parent_id).first()

        msg = Message.objects.create(
            conversation=conv,
            sender=sender,
            content=content,
            parent_message=parent
        )
        return {
            "id": msg.id,
            "conv_id": conv_id,
            "sender_id": sender.user_id,
            "sender_username": sender.username,
            "parent_id": parent.id if parent else None,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "is_recalled": False,
        }

    @sync_to_async
    def get_other_user_id(self, conv_id, me):
        # 1v1 会话只有两条 participant 记录
        return Conversation.objects.get(pk=conv_id).participants.exclude(user_id=me).first().user_id

    @sync_to_async
    def get_other_user_ids(self, conv_id, me) -> list[int]:
        return list(
            Conversation.objects.get(pk=conv_id)
            .participants
            .exclude(user_id=me)
            .values_list("user_id", flat=True)
        )

    @sync_to_async
    def is_group(self, conv_id) -> bool:
        return Conversation.objects.get(pk=conv_id).type == 'group'

    # ---------- 连接 ----------
    async def connect(self):
        # 前端连接 ws/chat/<conv_id>/
        self.conv_id = int(self.scope['url_route']['kwargs']['conv_id'])
        self.room_group = f'chat_{self.conv_id}'
        await self.validate_user()
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        # ✅ 关键：再加一个“个人收件箱”
        self.inbox_group = f'user_{self.user_id}'
        await self.channel_layer.group_add(self.inbox_group, self.channel_name)
        await self.accept()
        now = datetime.now()
        now_time = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f'[WS] {self.user_id} 加入房间 {self.room_group} 加入时间 {now_time}')
        print(f'[WS] {self.user_id} 加入房间 {self.inbox_group} 加入时间 {now_time}')

    # ---------------- 断开 ----------------
    async def disconnect(self, code):
        if self.room_group:
            await self.channel_layer.group_discard(self.room_group, self.channel_name)
        if hasattr(self, 'inbox_group'):
            await self.channel_layer.group_discard(self.inbox_group, self.channel_name)
        now = datetime.now()
        now_time = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f'[WS] {self.channel_name} 离开房间 {self.room_group} 离开时间 {now_time}')
        raise StopConsumer()

    # ---------------- 收到消息 ----------------
    async def receive(self, text_data=None, bytes_data=None):
        # 心跳探测
        if text_data == '__ping__':
            await self.send('__pong__')
            return

        # 2. 解析业务 JSON
        try:
            data = json.loads(text_data)
        except Exception:
            return  # 非法格式直接丢弃
        content = data.get('text', '').strip()
        if not content:
            return
        parent_id = data.get("parent_id")  # 可选：回复哪条消息
        print(f'[WS] 收到消息：{content}')

        # ---------- 校验是否是好友 ----------
        conv = await sync_to_async(Conversation.objects.get)(pk=self.conv_id)
        if conv.type == 'private':
            if not await self.both_in_private(conv):
                await self.channel_layer.group_send(
                    self.inbox_group,
                    {
                        "type": "inbox.notify",
                        "state": 403,
                        "payload": {
                            "content": "对方已解除好友，无法发送消息",
                        },
                    }
                )
                return
        
        # 5. 落库（异步）
        try:
            payload = await self.save_message(
                conv_id=self.conv_id,
                sender_id=self.user_id,
                content=content,
                parent_id=parent_id
            )
        except (Conversation.DoesNotExist, User.DoesNotExist, ValidationError) as e:
            # 失败可以给前端一个错误码，这里简单打印
            print("[WS] 落库失败:", e)
            return

        # 6. 回播给整个房间
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat.message",
                "state": 200,
                "payload": payload  # 把完整 dict 发出去
            }
        )
        # 2. 投到收件箱
        if await self.is_group(self.conv_id):
            # 群聊：给所有其他成员推送
            other_uids = await self.get_other_user_ids(self.conv_id, self.user_id)
            for uid in other_uids:
                await self.channel_layer.group_send(
                    f'user_{uid}',
                    {"type": "inbox.notify", "state": 200, "payload": payload}
                )
        else:
            other_uid = await self.get_other_user_id(self.conv_id, self.user_id)
            await self.channel_layer.group_send(
                f'user_{other_uid}',
                {"type": "inbox.notify", "state": 200, "payload": payload}
            )

    async def chat_message(self, event):
        # 给客户端发送消息 - 群组
        await self.send(text_data=json.dumps({
            "type": "normal",
            "state": event['state'],
            "msg": event['payload'],
        }))

    async def inbox_notify(self, event):
    # 推送到个人
        await self.send(text_data=json.dumps({
            "type": "inbox",
            "state": event['state'],
            "msg": event["payload"]
        }))

    @sync_to_async
    def validate_user(self):
        r_token = self.scope['cookies']['refresh_token']
        decoded = decode_refresh_token(r_token)

        if decoded['state'] == 1:
            self.user_id = decoded['data']['user_id']
        else:
            return self.send({
                "state": 401,
                "msg": '用户身份验证失败'
            })

    @sync_to_async
    def both_in_private(self, conv: Conversation) -> bool:
        """私聊：校验双方是否仍在会话里"""
        if conv.type != 'private':
            return True
        # 私聊：检查两人是否都还在 participants 表里
        uid1, uid2 = conv.private_members
        other_id = uid1 if self.user_id != uid1 else uid2
        return (
            conv.participants.filter(user_id=self.user_id).exists() and
            conv.participants.filter(user_id=other_id).exists()
        )

