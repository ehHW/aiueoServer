import json
import os
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
        # 把需要回给前端字段一次性读出
        return {
            "id": msg.id,
            "conv_id": conv_id,
            "sender_id": sender.user_id,
            "sender_username": sender.username,
            "parent_id": parent.id if parent else None,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),  # ISO 8601
            "is_recalled": False,
        }

    @sync_to_async
    def get_other_user_id(self, conv_id, me):
        # 1v1 会话只有两条 participant 记录
        return Conversation.objects.get(pk=conv_id).participants.exclude(user_id=me).first().user_id
    # ---------- 连接 ----------
    async def connect(self):
        # 前端连接 ws/chat/<conv_id>/
        self.conv_id = int(self.scope['url_route']['kwargs']['conv_id'])
        self.room_group = f'chat_{self.conv_id}'
        self.validate_user()
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        # ✅ 关键：再加一个“个人收件箱”
        self.inbox_group = f'user_{self.user_id}'
        await self.channel_layer.group_add(self.inbox_group, self.channel_name)
        await self.accept()
        print(f'[WS] {self.channel_name} 加入房间 {self.room_group}')
        print(f'[WS] {self.channel_name} 加入房间 {self.inbox_group}')

    # ---------------- 断开 ----------------
    async def disconnect(self, code):
        if self.room_group:
            await self.channel_layer.group_discard(self.room_group, self.channel_name)
        if hasattr(self, 'inbox_group'):
            await self.channel_layer.group_discard(self.inbox_group, self.channel_name)
        print(f'[WS] {self.channel_name} 离开房间 {self.room_group}')
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
                "payload": payload  # 把完整 dict 发出去
            }
        )
        # 2. 投到收件箱
        other_uid = await self.get_other_user_id(self.conv_id, self.user_id)
        await self.channel_layer.group_send(
            f'user_{other_uid}',
            {"type": "inbox.notify", "payload": payload}
        )

    async def chat_message(self, event):
        # print('chat_message', event)
        # 给客户端发送消息 - 群组
        await self.send(text_data=json.dumps({
            "type": "normal",
            'msg': event['payload'],
        }))
    
    async def inbox_notify(self, event):
    # 只推送，不追加 DOM，前端自己决定是弹窗还是未读+1
        await self.send(text_data=json.dumps({
            "type": "inbox",
            "msg": event["payload"]
        }))
    
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



# 给客户端发送消息 - 群组
        # await self.channel_layer.group_send(
        #     self.room_group,
        #     {
        #         'type': 'chat.message',   # 注意： Channels 要求用点号
        #         'msg': content,
        #     }
        # )
        # # 给客户端发送消息 - 个人
        # await self.send(text_data=json.dumps({
        #     'msg': msg,
        # }))