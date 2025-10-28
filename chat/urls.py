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
    path('conversations/group/', views.create_group),
    path('conversations/', views.list_conversations),
    path('conversations/private/', views.get_or_create_private),
    # 消息相关
    path('messages/send/', views.send_message),
    path('messages/', views.list_messages),
    path('messages/mark-read/', views.mark_as_read),
]