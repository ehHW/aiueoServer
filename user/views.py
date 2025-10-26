import re

from django.http import JsonResponse

from .models import User, Role, Permission, Permission2, CaiDan
from datetime import datetime
from django.utils import timezone

from django.core.paginator import Paginator
from utils.user import get_user, get_a_token
from utils import token
from utils.response import success_response, error_response
from datetime import timedelta


def verify_auth(userid, permission) -> bool:
    user = User.objects.get(user_id__exact=userid)
    role = Role.objects.get(role_id__exact=user.role_id)
    permissions = [_.permission2_id for _ in role.permission2.all()]
    return permission in permissions


def test(request):
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')
    return success_response()


def login(request):
    if request.method != 'POST':
        return error_response(405, "请求方法不允许")

    # 获取请求参数
    mobile = request.POST.get('mobile')
    password = request.POST.get('password')
    try:
        # 用户认证
        user = User.objects.get(mobile__exact=mobile)
        if user.password == password:
            access_token = token.create_access_token(user.user_id, user.role_id)
            r_token = token.create_refresh_token(user.user_id, user.role_id)
            response_data = {
                'state': 200,
                'msg': '登录成功',
                'data': {
                    'token': access_token,
                    'user_id': user.user_id,
                    'mobile': user.mobile,
                    'username': user.username,
                    'avatar': f"{user.avatar}",
                    'role_id': user.role_id,
                    'role_name': Role.objects.get(role_id__exact=user.role_id).role_name,
                    'expires_in': token.effective_minutes * 60
                }
            }

            # 返回带token的响应
            response =  JsonResponse(response_data, status=200)
            # 设置 Refresh Token 到安全 Cookie
            response.set_cookie(
                key='refresh_token',  # Cookie 名称
                value=r_token,  # Refresh Token 值
                max_age=timedelta(days=7).total_seconds(),  # 7天有效期
                httponly=True,  # 禁止 JavaScript 访问
                secure=True,  # 仅 HTTPS 传输（本地开发可设为 False）
                samesite='None',  # 防止 CSRF 攻击
                path='/',  # 限制 Cookie 路径
                # domain='127.0.0.1',  # 指定生效域名
            )
            return response
        else:
            return error_response(401, '用户名或密码错误')
    except Exception as e:
        return error_response(500, '服务器内部错误')


def logout(request):
    response = JsonResponse({
        "state": 200,
        "msg": "退出成功",
        "data": None
    })
    response.delete_cookie('refresh_token')  # 显式删除 Cookie
    return response


def refresh_token(request):
    if request.method != 'POST':
        return error_response(405, 'Method Not Allowed')
    r_token = request.COOKIES.get('refresh_token')
    if not r_token:
        return error_response(401, "Refresh token missing")

    decoded = token.decode_refresh_token(r_token)

    if decoded['state'] == 1:
        user_id = decoded['data']['user_id']
        role_id = decoded['data']['role_id']
        user = User.objects.get(user_id__exact=user_id)
        if user.role_id == role_id:
            access_token = token.create_access_token(user.user_id, user.role_id)
            return success_response({
                'token': access_token,
                'expires_in': token.effective_minutes * 60
            }, '刷新成功')
        else:
            return error_response(400, "User role mismatch")

    elif decoded['state'] == 2:
        return error_response(402, decoded['msg'])
    else:
        return error_response(403, decoded['msg'])


def create_user(request):
    create_user_permission2_id = 7
    """
    用户注册接口
    user_id: number
    username: string
    password: string
    mobile: string
    avatar?: string
    支持响应：
    - 201 Created: 注册成功
    - 400 Bad Request: 参数错误
    - 405 Method Not Allowed: 非POST请求
    - 409 Conflict: 手机号已注册
    - 500 Internal Server Error: 服务器异常
    """
    if request.method != 'POST':
        return error_response(405, 'Method Not Allowed')
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, create_user_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    # 手机号正则表达式（中国标准）
    MOBILE_REGEX = r'^1[3-9]\d{9}$'

    try:
        # 2. 参数提取与基本校验
        required_fields = ['mobile', 'username', 'password']
        data = {
            'mobile': request.POST.get('mobile'),
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
            'avatar': ''  # 需要处理文件上传逻辑
        }
        # 3. 必填参数校验
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return error_response(400, f"缺少必要参数: {','.join(missing)}")

        # 4. 手机号格式验证
        if not re.match(MOBILE_REGEX, data['mobile']):
            return error_response(400, "手机号格式错误")

        if not (2 <= len(data['username']) <= 6):
            return error_response(400, "用户名格式错误")

        # 5. 密码强度校验（可扩展正则表达式）
        if not (6 <= len(data['password']) <= 16):
            return error_response(400, "密码长度6-16位")

        # 6. 手机号唯一性校验
        if User.objects.filter(mobile=data['mobile']).exists():
            return error_response(400, "手机号已注册")

        # 7. 创建用户（使用Django原生用户模型）
        user = User(
            username=data['username'],
            password=data['password'],
            mobile=data['mobile'],
            avatar=''
        )
        user.save()
        # 8. 创建成功响应（包含必要用户信息）
        return success_response(
            message="用户创建成功",
            data={
                'user_id': user.user_id,
                'username': user.username,
                'mobile': user.mobile,
                'avatar': user.avatar if user.avatar else ''
            },
        )

    except Exception as e:
    # 记录异常日志（建议使用logging模块）
        print(f"注册异常: {str(e)}")
        return error_response(500, "服务器内部错误")


def user_list(request):
    user_list_permission2_id = 6
    def convert_tstamp_to_iso(timestamp: str) -> datetime:
        seconds = int(timestamp) // 1000
        aware_time = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return aware_time
    """
    请求
    pagenum: number
    pagesize: number
    username: string
    mobile: string
    role_name: string
    created_at: string
    updated_at: string
    """
    if request.method != 'GET':
        return error_response(405, 'Method Not Allowed')
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, user_list_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    pagenum = request.GET.get('pagenum')
    pagesize = request.GET.get('pagesize')
    username = request.GET.get('username')
    mobile = request.GET.get('mobile')
    role_name = request.GET.get('role_name')
    created_at = request.GET.get('created_at')
    updated_at = request.GET.get('updated_at')
    try:
        pagenum = int(pagenum) if pagenum else 1
        pagesize = int(pagesize) if pagesize else 10
    except Exception as e:
        pass

    users = User.objects.all().order_by("-user_id")  # 示例查询
    if username:
        users = User.objects.filter(username__exact=username)
    elif mobile:
        users = users.filter(mobile__exact=mobile)
    elif role_name:
        users = users.filter(role_name__exact=role_name)
    elif created_at:
        if created_at.__len__() == 27:
            created_at = list(map(convert_tstamp_to_iso, created_at.split('-')))
            users = users.filter(created_at__range=(created_at[0], created_at[1]))
    elif updated_at:
        if updated_at.__len__() == 27:
            updated_at = list(map(convert_tstamp_to_iso, updated_at.split('-')))
            users = users.filter(updated_at__range=(updated_at[0], updated_at[1]))
    else:
        pass
    paginator = Paginator(users, pagesize)
    page_obj = paginator.get_page(pagenum)  # 自动处理无效页码
    # 构建响应数据
    u_list = []
    for user in page_obj:
        u_list.append({
            'user_id': user.user_id,
            'username': user.username,
            'mobile': user.mobile,
            'avatar': f"{user.avatar}",
            'state': user.state,
            'role_name': user.role.role_name,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'role_id': user.role.role_id,
        })
    response_data = {
        'state': 200,
        'msg': '用户列表获取成功',
        "current_page": page_obj.number,
        "page_size": pagesize,
        'total': paginator.count,
        'total_pages': paginator.num_pages,
        'list': u_list
    }
    # 返回带token的响应
    return JsonResponse(response_data, status=200)


def update_user(request):
    update_user_permission2_id = 7
    if request.method != 'POST':
        return error_response(405, "Method Not Allowed")
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, update_user_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
        # 手机号正则表达式（中国标准）
    MOBILE_REGEX = r'^1[3-9]\d{9}$'

    try:
        # 2. 参数提取与基本校验
        required_fields = ['mobile', 'username', 'user_id']
        data = {
            'user_id': request.POST.get('user_id'),
            'mobile': request.POST.get('mobile'),
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
            'avatar': ''  # 需要处理文件上传逻辑
        }
        # 3. 必填参数校验
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return error_response(400, f"缺少必要参数: {','.join(missing)}")

        # 4. 手机号格式验证
        if not re.match(MOBILE_REGEX, data['mobile']):
            return error_response(400, "手机号格式错误")

        if not (2 <= len(data['username']) <= 6):
            return error_response(400, "用户名格式错误")

        user = User.objects.get(user_id__exact=data['user_id'])
        # 6. 手机号唯一性校验
        if user.mobile != data['mobile'] and User.objects.filter(mobile__exact=data['mobile']).exists():
            return error_response(400, "手机号已注册")
        user.username = data['username']
        user.mobile = data['mobile']
        if not data['password']:
            pass
        else:
            if 6 <= len(data['password']) <= 16:
                user.password = data['password']
            else:
                return error_response(400, "密码长度6-16位")
        user.save()
        return success_response(message="更新用户成功")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def change_user_role(request):
    change_user_role_permission2_id = 9
    """
    请求
    username: string
    role_name: string
    user_id: number
    role_id: number
    """
    if request.method != 'POST':
        return error_response(405, "Method Not Allowed")
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, change_user_role_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    user_id = request.POST.get('user_id')
    role_id = request.POST.get('role_id')
    role_name = request.POST.get('role_name')
    try:
        if user_id and role_id and role_name:
            user = User.objects.get(user_id__exact=user_id)
            user.role_id = role_id
            user.role_name = role_name
            user.save()
            return success_response(message="更新角色成功")
        else:
            return error_response(400, "请求参数错误")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def delete_user(request):
    delete_user_permission2_id = 7
    if request.method != 'POST':
        return error_response(405, "Method Not Allowed")
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, delete_user_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    try:
        del_user_id = request.POST.get('del_user_id')
        user = User.objects.get(user_id__exact=del_user_id)
        user.delete()
        return success_response(message="用户删除成功")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def role_list(request):
    """
    请求
    pagenum: number
    pagesize: number
    role_name: string
    响应
    action_list: string
    auth_ids: string
    auth_ids_son: string
    created_at: string
    role_desc: string
    role_id: number
    role_name: string
    updated_at: string
    """
    role_list_permission2_id = 8
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, role_list_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    r_list = []
    roles = Role.objects.all().order_by("role_id")
    pagenum = request.GET.get('pagenum')
    pagesize = request.GET.get('pagesize')
    role_name = request.GET.get('role_name')
    try:
        if role_name:
            roles = roles.filter(role_name__exact=role_name)

        paginator = Paginator(roles, pagesize)
        page_obj = paginator.get_page(pagenum)  # 自动处理无效页码

        for role in page_obj:
            permissions = role.permission.all()
            auth_ids = ','.join([f'{_.permission_id}' for _ in permissions])
            auth_ids_son = ','.join(f'{_.permissions.first().permission_id}0{_.permission2_id}' for _ in role.permission2.all())
            r_list.append({
                'role_id': role.role_id,
                'role_name': role.role_name,
                'created_at': role.created_at,
                'updated_at': role.updated_at,
                'role_desc': role.role_desc,
                'action_list': 'action_list',
                'auth_ids': auth_ids,
                'auth_ids_son': auth_ids_son
            })
        return JsonResponse({
            'state': 200,
            'msg': '角色列表获取成功',
            "current_page": page_obj.number,
            "page_size": pagesize,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
            'list': r_list
        })
    except Exception as e:
        return error_response(500, "服务器内部错误")


def create_role(request):
    create_role_permission2_id = 9
    if request.method != 'POST':
        return error_response(405, "Method Not Allowed")
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, create_role_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    role_name = request.POST.get('role_name')
    role_desc = request.POST.get('role_desc')
    try:
        role = Role(role_name=role_name, role_desc=role_desc)
        role.save()
        return success_response(message="创建角色成功")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def update_role(request):
    """
    role_id: number
    role_name: string
    role_desc?: string
    """
    update_role_permission2_id = 9
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, update_role_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    role_id = request.POST.get('role_id')
    role_name = request.POST.get('role_name')
    role_desc = request.POST.get('role_desc')
    try:
        role = Role.objects.get(role_id__exact=role_id)
        role.role_name = role_name
        role.role_desc = role_desc
        role.save()
        return success_response(message="更新角色成功")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def delete_role(request):
    delete_role_permission2_id = 9
    if request.method != 'POST':
        return error_response(405, "Method Not Allowed")
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, delete_role_permission2_id):
            return error_response(400, '权限不足')
    except:
        return error_response(400, '用户id错误')
    try:
        role_id = request.POST.get('role_id')
        role = Role.objects.get(role_id__exact=role_id)
        role.delete()
        return success_response(message="删除角色成功")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def change_role_permission(request):
    """
    role_name: string
    role_id: number
    auth_ids: string
    auth_ids_son: string
    1 超级管理员 1,2,3,4,5 101,102,203,204,205,306,307,408,409,5010,5011
    """
    change_role_permission_permission2_id = 11
    if request.method != 'POST':
        return error_response(405, "Method Not Allowed")
    try:
        a_token = get_a_token(request)
        user = get_user(a_token)
        if not user:
            return error_response(401, message='用户认证失败')

        if not verify_auth(user.user_id, change_role_permission_permission2_id):
            return error_response(400, '权限不足')

        user_id = request.POST.get('user_id')
        if int(user_id) == 1:
            return error_response(400, '禁止修改此角色')
    except:
        return error_response(400, '用户id错误')
    role_id = request.POST.get('role_id')
    role_name = request.POST.get('role_name')
    auth_ids = request.POST.get('auth_ids')
    try:
        role = Role.objects.get(role_id__exact=role_id)
        auth_ids = list(map(int, auth_ids.split(',')))
        auth_ids_son = request.POST.get('auth_ids_son')
        auth_ids_son = list(map(lambda x: int(x[1:]), auth_ids_son.split(',')))
        permission = Permission.objects.filter(permission_id__in=auth_ids)
        permission2 = Permission2.objects.filter(permission2_id__in=auth_ids_son)
        role.permission.set(permission)
        role.permission2.set(permission2)
        return success_response(message="角色权限更新成功")
    except Exception as e:
        return error_response(500, "服务器内部错误")


def menu_list(request):
    """
    role_id: number
    """
    a_token = get_a_token(request)
    user = get_user(a_token)
    if not user:
        return error_response(401, message='用户认证失败')

    try:
        role_id = user.role_id
        role = Role.objects.get(role_id__exact=role_id)
        caidan2s_all = [_.caidan2 for _ in role.permission2.all()]
        caidans = list(set(CaiDan.objects.get(auth_id__exact=_.auth_pid) for _ in caidan2s_all))
        data = []
        for menu_item in caidans:
            caidan2s = [_ for _ in caidan2s_all if _.auth_pid == menu_item.auth_id]
            data.append({
                'auth_id': menu_item.auth_id,
                'icon': menu_item.icon,
                'auth_name': menu_item.auth_name,
                'path': menu_item.path,
                'type': menu_item.type,
                'auth_pid': menu_item.auth_pid,
                'auth_pname': menu_item.auth_pname,
                'keep_alive': menu_item.keep_alive,
                'component': menu_item.component,
                'sort': menu_item.sort,
                'created_at': menu_item.created_at,
                'updated_at': menu_item.updated_at,
                'children': [{
                    'auth_id': int(f'{menu_item.auth_id}0{_.auth_id}'),
                    'icon': _.icon,
                    'auth_name': _.auth_name,
                    'path': _.path,
                    'type': _.type,
                    'auth_pid': _.auth_pid,
                    'auth_pname': _.auth_pname,
                    'keep_alive': _.keep_alive,
                    'component': _.component,
                    'sort': _.sort,
                    'created_at': _.created_at,
                    'updated_at': _.updated_at,
                } for _ in caidan2s]
            })

        return success_response(message="获取菜单列表成功", data=data)
    except Exception as e:
        return error_response(500, "服务器内部错误")

