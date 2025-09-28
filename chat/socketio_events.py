import time

import socketio

# 创建Socket.IO实例
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# 连接事件
@sio.event
async def connect(sid, environ):
    print(f"客户端 {sid} 已连接")
    await sio.emit('response', {'message': '连接成功'}, to=sid)

@sio.event
async def disconnect(sid, environ):
    print(f"客户端 {sid} 已断开连接")

# 消息事件
@sio.event
async def chat_msg(sid, data):
    print(f"收到消息: {data}")
    # 广播消息给所有客户端
    await sio.emit('chat_msg', {
        'text': data.get('msg', ''),
        'timestamp': time.time()
    })

# 断开连接事件
@sio.event
async def disconnect(sid):
    print(f"客户端 {sid} 断开连接")
