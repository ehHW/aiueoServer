from . import token
from user.models import User
from utils.response import error_response


def get_user(a_token):
    decoded = token.decode_access_token(a_token)
    if decoded['state'] == 1:
        user_id = decoded['data']['user_id']
        user = User.objects.get(user_id__exact=user_id)
        return user
    else:
        return None


def get_a_token(request):
    authorization = request.headers.get('Authorization')
    if not authorization:
        return error_response(401, message='无效 Authorization')
    try:
        a_token = authorization.split(' ')[1]
        if not a_token:
            return error_response(401, message='无效 Authorization')
        return a_token
    except IndexError:
        return error_response(401, message='无效 Authorization')
    except Exception as e:
        return error_response(500, message='服务器内部错误')