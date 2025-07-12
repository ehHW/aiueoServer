import random

import requests

url = "http://127.0.0.1:8000/user/create/"
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

def random_number():
    res = ''
    for _ in range(0, 9):
        res += str(random.randint(0, 9))
    return res




for i in range(0, 500):
    data = {
        'username': f'qwe{i}',
        'password': '888888',
        'mobile': f'1{random.randint(3, 9)}{random_number()}',
        'avatar': ''
    }
    requests.post(url, headers=headers, data=data)
    print(i)
