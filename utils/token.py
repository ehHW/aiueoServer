import jwt
from datetime import datetime, timedelta, UTC  # Python 3.11+ 专用

import secrets


"""
用户登录 → 服务端返回 access_token 和 refresh_token

API 请求 → 客户端在请求头携带 access_token

Access Token 过期 → 客户端用 refresh_token 请求新的 access_token

刷新成功 → 服务端返回新 access_token，refresh_token 通常不变（可配置是否刷新）

Refresh Token 过期 → 强制用户重新登录
"""
JWT_ACCESS_KEY = "MSMj8y6KfoEcjpiACUdtoBnwRBWaEC23leqQwEQGgjg"
JWT_REFRESH_KEY = "q4tLWwfGX7Arr8cAIIAGEclPPShMx6_SRcqAzkNeq9g"
effective_minutes = 1


def create_key():
    # 生成一个安全的 HS256 密钥（32 字节随机数据，Base64 编码）
    key = secrets.token_urlsafe(32)
    print("Key:", key)
    return key


def create_access_token(user_id, role_id) -> bytes:
    # 定义 payload
    payload = {
        "user_id": user_id,  # 用户ID
        "role_id": role_id,  # 角色ID
        "exp": datetime.now(UTC) + timedelta(minutes=effective_minutes),  # 有效期1分钟
        "iat": datetime.now(UTC)  # 签发时间
    }
    token = jwt.encode(
        payload=payload,
        key=JWT_ACCESS_KEY,
        algorithm="HS256"
    )
    return token


def create_refresh_token(user_id, role_id) -> bytes:
    payload = {
        "user_id": user_id,  # 用户ID
        "role_id": role_id,  # 角色ID
        "exp": datetime.now(UTC) + timedelta(days=7),  # 有效期7天
        "iat": datetime.now(UTC)
    }
    token = jwt.encode(
        payload=payload,
        key=JWT_REFRESH_KEY,
        algorithm="HS256"
    )
    return token


def decode_access_token(token: bytes) -> dict:
    res = {
        "state": 1,
        "msg": "",
        "data": None
    }
    global JWT_ACCESS_KEY
    try:
        decoded = jwt.decode(
            token,
            JWT_ACCESS_KEY,
            algorithms=["HS256"],  # 指定算法
            options={"require_exp": True}  # 检查过期时间
        )
    except jwt.ExpiredSignatureError:
        res["state"] = 2
        res["msg"] = "Token 已过期"
        return res
    except jwt.InvalidTokenError as e:
        res["state"] = 3
        res["msg"] = "无效 Token"
        return res
    res['data'] = decoded
    return res


def decode_refresh_token(token: bytes) -> dict:
    res = {
        "state": 1,
        "msg": "",
        "data": None
    }
    try:
        decoded = jwt.decode(
            token,
            JWT_REFRESH_KEY,
            algorithms=["HS256"],  # 指定算法
            options={"require_exp": True}  # 检查过期时间
        )
    except jwt.ExpiredSignatureError:
        res["state"] = 2
        res["msg"] = "Token 已过期"
        return res
    except jwt.InvalidTokenError as e:
        res["state"] = 3
        res["msg"] = "无效 Token"
        return res
    res['data'] = decoded
    return res


# 创建秘钥
# create_key()

# print(decode_access_token(create_access_token(5, 5)))