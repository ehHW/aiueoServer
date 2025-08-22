from django.urls import path
from . import views


app_name = 'user'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('refresh_token/', views.refresh_token, name='refresh_token'),
    path('user_list/', views.user_list, name='user_list'),
    path('create_user/', views.create_user, name='create_user'),
    path('update_user/', views.update_user, name='update_user'),
    path('delete_user/', views.delete_user, name='delete_user'),
    path('role_list/', views.role_list, name='role_list'),
    path('create_role/', views.create_role, name='create_role'),
    path('change_user_role/', views.change_user_role, name='change_user_role'),
    path('update_role/', views.update_role, name='update_role'),
    path('delete_role/', views.delete_role, name='delete_role'),
    path('change_role_permission/', views.change_role_permission, name='change_role_permission'),
    path('menu_list/', views.menu_list, name='menu_list'),
    # path('connect_permission_permission2/', views.connect_permission_permission2, name='connect_permission_permission2'),
    # path('create_menu/', views.create_menu, name='create_menu'),
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


    path('test/', views.test),
]