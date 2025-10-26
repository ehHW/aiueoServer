from django.http import JsonResponse


def error_response(status_code, message, data=None):
    """生成标准错误响应"""
    return JsonResponse({
        'state': status_code,
        'msg': message,
        'data': data
    }, status=status_code)


def success_response(data=None, message=None):
    """生成标准成功响应"""
    return JsonResponse({
        'state': 200,
        'msg': message,
        'data': data
    }, status=200)