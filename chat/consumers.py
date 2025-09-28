# ---------------------------------django-channels------------------------------------
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_name = None
        self.room_group_name = None

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        print("connected")
        # 将channel加入群组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        print('disconnect')
        # 将channel从群组中移除
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        msg = text_data_json['msg']
        print(msg)
        # username = text_data_json.get('username', 'Anonymous')
        #
        # 向群组发送消息
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'msg': msg,
            }
        )

        # # 给客户端发送消息 - 个人
        # await self.send(text_data=json.dumps({
        #     'msg': msg,
        # }))

    async def chat_message(self, event):
        msg = event['msg']
        # 给客户端发送消息 - 群组
        await self.send(text_data=json.dumps({
            'msg': msg,
        }))