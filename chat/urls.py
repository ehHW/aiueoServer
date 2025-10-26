from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    # 好友相关
    path('friends/request/add/', views.send_friend_request),
    path('friends/request/list/', views.friend_request_list),
    path('friends/request/handle/', views.handle_friend_request),
    path('friends/', views.friend_list),
    # 会话相关
    path('conversations/group/', views.create_group_chat),
    path('conversations/', views.conversation_list),
    # 消息相关
    path('messages/send/', views.send_message),
    path('messages/history/', views.message_history),
    path('messages/mark-read/', views.mark_as_read),
]