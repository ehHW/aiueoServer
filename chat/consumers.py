import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_name = None
        self.room_group_name = None

    # ---------------- 连接 ----------------
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'group_chat_{self.room_name}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f'[WS] {self.channel_name} 加入房间 {self.room_group_name}')

    # ---------------- 断开 ----------------
    async def disconnect(self, code):
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f'[WS] {self.channel_name} 离开房间 {self.room_group_name}')
        raise StopConsumer()


    # ---------------- 收到消息 ----------------
    async def receive(self, text_data=None, bytes_data=None):
        try:
            # 心跳探测
            if text_data == '__ping__':
                await self.send('__pong__')
                return

            # 正常聊天消息
            data = json.loads(text_data)
            msg = data.get('msg')
            if not msg:
                return

            print(f'[WS] 收到消息：{msg}')
            # 给客户端发送消息 - 群组
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',   # 注意： Channels 要求用点号
                    'msg': msg,
                }
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'get.user',   # 注意： Channels 要求用点号
                    'msg': msg, 
                }
            )
        except json.JSONDecodeError:
            print('[WS] 非法 JSON，忽略')

        # # 给客户端发送消息 - 个人
        # await self.send(text_data=json.dumps({
        #     'msg': msg,
        # }))

    async def chat_message(self, event):
        print('chat_message', event)
        msg = event['msg']
        # 给客户端发送消息 - 群组
        await self.send(text_data=json.dumps({
            'msg': msg,
        }))

    async def get_user(self, event):
        print('get_user', event)