import secrets
import string

def generate_jwt_secret(length=64):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# 生成示例
print(generate_jwt_secret())  # 输出示例：h#xK9Lm^2pR&vGfE@wT8YsD3qZb!jA
