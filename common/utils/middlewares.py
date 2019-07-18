"""

书写
需求：对于所有的视图，无论是否强制要求用户登录，都在视图中获取用户认证后的身份信息
"""
from flask import request, g

from utils.jwt_util import verify_jwt


def jwt_authentication():
    """
    作用：获取用户认证后的身份信息，这个身份信息是给视图函数去用的
    （这里面的代码什么时候执行：在所有视图函数执行之前执行 ）
    
    
    # 1、获取请求头中的token
    # 2、验证token（如果获取到touken不为空而且格式正确）
    # 3、保存到g对象中（如果payload不为None保存到g对象中）
    
    
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzb21lIjoicGF5bG9hZCJ9.4twFt5NiznN84AWoo1d7KO1T_yoc0Z6XOpOVswacPZg
    :return: 
    """
    g.user_id = None   # 声明两个变量的初始值
    g.is_refresh = False

    # 1、获取请求头中的token
    token = request.headers.get("Authorization")

    # 2、验证token（如果获取到touken不为空而且格式正确）

    if token is not None and token.startswith("Bearer "):
        token = token[7:]

        payload = verify_jwt(token, secret=None)
        # 3、保存到g对象中（如果payload不为None保存到g对象中）
        if payload is not None:  # 不为空，才能拿到值，就可以保存到g对象中
            g.user_id = payload.get("user_id")
            g.is_refresh = payload.get("is_refresh", False)


