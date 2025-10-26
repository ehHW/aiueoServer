# chat/views.py
from django.http import HttpResponse, JsonResponse
from .models import Conversation, ConversationParticipant, FriendRequest, Message
from user.models import User
from utils.user import get_user
from utils.response import success_response, error_response
from utils.user import get_a_token, get_user

from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import models


# ---------------------------------django-channels------------------------------------
def index(request):
    return HttpResponse('Hello, world. You\'re at the polls room.')


#-----------------好友相关--------------------
# 发送好友请求
def send_friend_request(request):
    if request.method != "POST":
        return error_response(405, "Method not allowed")
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    receiver_id = request.POST.get('receiver_id')
    if not receiver_id:
        return error_response(400, '缺少必要参数')
    try:
        receiver_id = int(request.POST.get("receiver_id"))
    except (ValueError, TypeError):
        return error_response(400, "receiver_id 必须是整数")

    try:
        receiver = User.objects.get(user_id__exact=receiver_id)  # 根据你的用户表结构调整
        if receiver == user:
            return error_response(400, '不能添加自己为好友')

        # 检查是否已存在请求（优化查询）
        # existing_request = FriendRequest.objects.filter(
        #     sender_id__in=[user.user_id, receiver.user_id],
        #     receiver_id__in=[user.user_id, receiver.user_id],
        #     status=FriendRequest.PENDING
        # ).exists()
        # if existing_request:
        #     return JsonResponse({'error': '已存在待处理的好友请求'}, status=400)
        # FriendRequest.objects.create(sender=user, receiver=receiver)

        req_obj, created = FriendRequest.objects.get_or_create(
            from_user_id=user.user_id,
            to_user_id=receiver_id,
            defaults={"status": FriendRequest.PENDING}
        )
        if not created:
            return error_response(409, "好友请求已存在")
        return success_response(message='好友请求已发送')
    except User.DoesNotExist:
        return error_response(404, '用户不存在')
    except Exception as e:
        return error_response(500, '服务器内部错误')


# 获取好友请求列表
def friend_request_list(request):
    if request.method != "GET":
        return error_response(405, "Method not allowed")
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    try:
        direction = request.GET.get("type", "in").strip().lower()
        if direction == "in":
            friend_requests = FriendRequest.objects.filter(to_user_id=user.user_id, status=FriendRequest.PENDING)
        else:
            friend_requests = FriendRequest.objects.filter(from_user_id=user.user_id, status=FriendRequest.PENDING)
        data = [{
            'sender_id': fr.from_user.user_id,
            'sender_username': fr.from_user.username,
            'sender_time': fr.created_at,
            'sender_avatar': fr.from_user.avatar if fr.from_user.avatar else None,
        } for fr in friend_requests]

        return success_response(data=data, message='好友请求列表获取成功')
    except Exception as e:
        return error_response(500, '服务器内部错误')


# 处理好友请求
def handle_friend_request(request):
    if request.method != "POST":
        return error_response(405, "Method not allowed")
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    action = request.POST.get('action')
    sender_id = request.POST.get('sender_id')
    if action not in ['accept', 'decline']:
        return error_response(400, '无效操作类型')

    try:
        req_obj = FriendRequest.objects.get(
            from_user_id=sender_id,
            to_user_id=user.user_id,
            status=FriendRequest.PENDING
        )
    except FriendRequest.DoesNotExist:
        return error_response(404, "请求不存在或已处理")

    req_obj.status = FriendRequest.ACCEPTED if action == "accept" else FriendRequest.DECLINED
    req_obj.save(update_fields=["status", "updated_at"])
    return success_response({"status": req_obj.status}, f"已{action}")


# 获取好友列表
def friend_list(request):
    if request.method != "GET":
        return error_response(405, "Method not allowed")
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    uid = user.user_id
    reqs = FriendRequest.objects.filter(
        status=FriendRequest.ACCEPTED
    ).filter(
        models.Q(from_user_id=uid) | models.Q(to_user_id=uid)
    )

    friends = []
    for r in reqs:
        if r.from_user_id == uid:
            friends.append({
                "user_id": r.to_user_id,
                "username": r.to_user.username,
                'avatar': r.to_user.avatar.url if r.to_user.avatar else None
                })
        else:
            friends.append({
                "user_id": r.from_user_id,
                "username": r.from_user.username,
                'avatar': r.from_user.avatar.url if r.from_user.avatar else None
                })
    return success_response(
        data=friends,
        message='好友列表获取成功'
    )


#-----------------会话相关--------------------
# 获取或创建私聊会话：确保为每对用户创建唯一的私聊会话
def get_or_create_private_conversation(user1, user2):
    conversations = Conversation.objects.filter(
        type=Conversation.PRIVATE,
        participants__user=user1
    ).filter(
        participants__user=user2
    ).distinct()
    if conversations.exists():
        return conversations.first()
    else:
        conversation = Conversation.objects.create(type=Conversation.PRIVATE, creator=user1)
        ConversationParticipant.objects.create(user=user1, conversation=conversation)
        ConversationParticipant.objects.create(user=user2, conversation=conversation)
        return conversation


# 创建群聊
def create_group_chat(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    name = request.POST.get('name', '新群聊')
    participant_ids = request.POST.getlist('participants')  # 用户ID列表

    if not participant_ids:
        return error_response(400, '至少需要选择一个参与者')

    try:
        # 创建会话
        conversation = Conversation.objects.create(
            type=Conversation.GROUP,
            name=name,
            creator=user
        )

        # 添加参与者（包括创建者）
        participants = {user}
        for uid in participant_ids:
            try:
                participants.add(User.objects.get(user_id=uid))
            except User.DoesNotExist:
                continue

        # 批量创建参与者
        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(user=u, conversation=conversation)
            for u in participants
        ])

        return success_response(
            data={
                'conversation_id': conversation.id,
                'name': conversation.name
            },
            message='群聊创建成功'
        )

    except Exception as e:
        return error_response(500, '群聊创建失败')


# 获取会话列表
def conversation_list(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')
    # 获取用户参与的所有会话
    # conversations = Conversation.objects.filter(
    #     participants__user=user
    # ).prefetch_related('participants__user', 'messages').order_by('-messages__timestamp')
    conversations = Conversation.objects.filter(
        participants__user=user
    ).prefetch_related(
        'participants__user',
        models.Prefetch('messages', queryset=Message.objects.order_by('-timestamp'))
    ).distinct()

    response_data = []
    for conv in conversations:
        # 获取最后一条消息（使用预取数据）
        last_message = conv.messages.first() if conv.messages.exists() else None

        # 获取未读消息数（优化查询）
        participant = conv.participants.get(user=user)
        unread_count = conv.messages.filter(
            timestamp__gt=participant.last_read
        ).count() if participant.last_read else conv.messages.count()

        # 构建会话名称
        if conv.type == Conversation.PRIVATE:
            other_user = conv.participants.exclude(user=user).first().user
            conv_name = other_user.username
        else:
            conv_name = conv.name

        response_data.append({
            'conversation_id': conv.id,
            'type': conv.type,
            'name': conv_name,
            'last_message': {
                'content': last_message.content if last_message else None,
                'timestamp': last_message.timestamp.isoformat() if last_message else None
            },
            'unread_count': unread_count
        })

    return success_response(
        data=sorted(response_data, key=lambda x: x['last_message']['timestamp'] or '', reverse=True),
        message='会话列表获取成功'
    )


#-----------------消息相关--------------------
# 发送消息
def send_message(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    conversation_id = request.POST.get('conversation_id')
    content = request.POST.get('content', '').strip()

    if not content:
        return error_response(400, '消息内容不能为空')

    try:
        conversation = Conversation.objects.get(id=conversation_id)
        # 验证用户是否在会话中
        if not conversation.participants.filter(user=user).exists():
            return JsonResponse({'error': '无权限发送消息'}, status=403)

        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content
        )
        # 实时消息推送逻辑（需要结合WebSocket实现）
        # 这里可以添加消息推送代码
        return success_response(
            data={
                'message_id': message.id,
                'timestamp': message.timestamp.isoformat()
            },
            message='消息发送成功'
        )

    except Conversation.DoesNotExist:
        return error_response(404, '会话不存在')
    except Exception as e:
        return error_response(500, '消息发送失败')


# 获取消息历史
def message_history(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    conversation_id = request.GET.get('conversation_id')
    if not conversation_id:
        return error_response(401, '房间获取失败')

    page = request.GET.get('page', 1)
    page_size = 20  # 每页消息数量

    try:
        conversation = Conversation.objects.get(id=conversation_id)
        if not conversation.participants.filter(user=user).exists():
            return error_response(403, '无访问权限')

        messages = conversation.messages.order_by('-timestamp')
        paginator = Paginator(messages, page_size)

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        return success_response(
            data={
                'messages': [{
                    'message_id': msg.id,
                    'sender_id': msg.sender.user_id,  # 根据用户表结构调整
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'parent_message_id': msg.parent_message_id
                } for msg in page_obj],
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next()
            },
            message='消息历史获取成功'
        )

    except Conversation.DoesNotExist:
        return error_response(404, '会话不存在')


# 标记消息已读
def mark_as_read(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    conversation_id = request.GET.get('conversation_id')
    if not conversation_id:
        return error_response(401, '房间获取失败')

    try:
        participant = ConversationParticipant.objects.get(
            user=user,
            conversation_id=conversation_id
        )
        participant.last_read = timezone.now()
        participant.save()
        return success_response(message='已标记为已读')
    except ConversationParticipant.DoesNotExist:
        return error_response(403, '无操作权限')