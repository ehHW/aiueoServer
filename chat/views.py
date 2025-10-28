# chat/views.py
import json
from typing import List
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Max, F, Q, OuterRef, Subquery

from .models import Conversation, ConversationParticipant, FriendRequest, Message
from user.models import User
from utils.user import get_user
from utils.response import success_response, error_response
from utils.user import get_a_token, get_user

from django.utils import timezone
from django.utils import timezone as dj_tz
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
        if FriendRequest.objects.filter(
            lesser_id=min(user.user_id, receiver_id),
            greater_id=max(user.user_id, receiver_id),
            status=FriendRequest.ACCEPTED
        ).exists():
            return error_response(400, '双方已经是好友')

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
@require_http_methods(["POST"])
def get_or_create_private(request):
    user = get_user(get_a_token(request))
    if not user:
        return error_response(401, '用户认证失败')
    target_id = request.POST.get('target_id')
    if not target_id:
        return error_response(400, '参数缺失')
    try:
        target_id = int(target_id)
    except TypeError:
        error_response(400, '参数错误')
    if target_id == user.user_id:
        return error_response(400, '不能和自己私聊')

    members = sorted([user.user_id, target_id])

    with transaction.atomic():
        # 唯一索引兜底，并发也安全
        conv, created = Conversation.objects.get_or_create(
            type=Conversation.PRIVATE,
            private_members=members,
            defaults={'creator': user}
        )
        if created:
            ConversationParticipant.objects.bulk_create([
                ConversationParticipant(user_id=uid, conversation=conv)
                for uid in members
            ])

    return success_response({'conversation_id': conv.id}, '私聊会话已建立')


# 创建群聊
@require_http_methods(["POST"])
def create_group(request):
    user = get_user(get_a_token(request))
    if not user:
        return error_response(401, '用户认证失败')

    name = request.POST.get('name')
    try:
        member_ids: List = json.loads(request.POST.get('member_ids'))
    except TypeError:
        error_response(400, '参数错误')
    if not name:
        return error_response(400, '群名称不能为空')
    if user.user_id not in member_ids:
        member_ids.append(user.user_id)
    if len(member_ids) < 2:
        return error_response(400, '至少再拉 1 人')

    with transaction.atomic():
        conv = Conversation.objects.create(
            type=Conversation.GROUP,
            name=name,
            creator=user
        )
        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(user_id=uid, conversation=conv)
            for uid in member_ids
        ])

    return success_response({'conversation_id': conv.id}, '群聊创建成功')


# 获取会话列表
@require_http_methods(["GET"])
def list_conversations(request):
    # ---------- 认证 ----------
    user = get_user(get_a_token(request))
    if not user:
        return error_response(401, '用户认证失败')

    # ---------- 子查询：最新消息 ----------
    last_msg_sq = Message.objects.filter(
        conversation=OuterRef('pk')
    ).order_by('-timestamp')[:1]

    # ---------- 主查询 ----------
    qs = (Conversation.objects
          .filter(participants__user=user)
          .annotate(
              last_msg_id=Subquery(last_msg_sq.values('id')[:1]),
              last_time=Subquery(last_msg_sq.values('timestamp')[:1])
          )
          .order_by('-last_time', '-created_at'))

    data = []
    for c in qs:
        # 未读数
        participant = c.participants.get(user=user)
        unread = max((c.last_msg_id or 0) - (participant.read_up_to_msg_id or 0), 0)

        # 私聊：拼对方昵称 + 头像
        if c.type == Conversation.PRIVATE:
            mate_uid = [uid for uid in c.private_members if uid != user.user_id][0]
            title = f'用户{mate_uid}'          # 没有 nickname，先拼一个
        else:
            title = c.name or f'群聊#{c.id}'   # 没有群头像字段

        data.append({
            'id': c.id,
            'type': c.type,
            'title': title,
            'unread': unread,
            'last_msg_id': c.last_msg_id,
            'last_time': c.last_time.timestamp() if c.last_time else None,
            'created_at': c.created_at.timestamp()
        })

    return success_response(data, '会话列表获取成功')


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
@require_http_methods(["GET"])
def list_messages(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    conversation_id = request.GET.get('conversation_id')
    if not conversation_id:
        return error_response(401, '房间获取失败')
    if not ConversationParticipant.objects.filter(
        conversation_id=conversation_id, user=user
    ).exists():
        return error_response(403, '你不在该会话中')
    try:
        last_msg_id = int(request.GET.get('last_msg_id', 0))
        limit = int(request.GET.get('limit', 20))
    except ValueError:
        return error_response(400, '分页参数非法')
    limit = max(1, min(limit, 50))          # 至少 1 条，最多 50
    
    qs = (Message.objects
          .filter(conversation_id=conversation_id, id__gt=last_msg_id)
          .select_related('sender')
          .order_by('timestamp')[:limit])

    # 6. 序列化
    data = []
    for m in qs:
        ts = m.timestamp
        if dj_tz.is_aware(ts):
            ts = ts.astimezone(timezone.utc)
        data.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_username': m.sender.username,
            'content': m.content,
            'timestamp': int(ts.timestamp() * 1000),
            'is_recalled': m.is_recalled,
            'parent_id': m.parent_message_id or 0,
        })
    return success_response(data)
    # page = request.GET.get('page', 1)
    # page_size = 20  # 每页消息数量
    # try:
    #     conversation = Conversation.objects.get(id=conversation_id)
    #     if not conversation.participants.filter(user=user).exists():
    #         return error_response(403, '无访问权限')

    #     messages = conversation.messages.order_by('-timestamp')
    #     paginator = Paginator(messages, page_size)

    #     try:
    #         page_obj = paginator.page(page)
    #     except PageNotAnInteger:
    #         page_obj = paginator.page(1)
    #     except EmptyPage:
    #         page_obj = paginator.page(paginator.num_pages)

    #     return success_response(
    #         data={
    #             'messages': [{
    #                 'message_id': msg.id,
    #                 'sender_id': msg.sender.user_id,  # 根据用户表结构调整
    #                 'content': msg.content,
    #                 'timestamp': msg.timestamp.isoformat(),
    #                 'parent_message_id': msg.parent_message_id
    #             } for msg in page_obj],
    #             'current_page': page_obj.number,
    #             'total_pages': paginator.num_pages,
    #             'has_next': page_obj.has_next()
    #         },
    #         message='消息历史获取成功'
    #     )

    # except Conversation.DoesNotExist:
    #     return error_response(404, '会话不存在')


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