from flask import request, g

from utils.jwt_util import verify_jwt

'''
需求：对于所有的视图，无论是否强制要求用户登录，都在视图中获取用户认证后的身份信息
'''

def jwt_authentication():
    #获取用户认证后的信息
    #设置初始值，以防获取不到参数时报错。。但是用户get方式获取不到user_id,is_refresh，不会报错。
    # 而用字典的键获取值时则会报错
    g.user_id =None
    g.is_refresh =False
    #1,获取请求头中的token
    token = request.headers.get("Authorization")
    #2,验证token (不为空且格式正确)
    if token is not None and token.startswith("Bearer "):
        token = token[7:]  #去除开头的 "Bearer",切片
        payload =verify_jwt(token,secret=None)
        #3,保存到g 对象中（payload不为None)
        if payload is not None:
            g.user_id = payload.get("user_id")
            g.is_refresh = payload.get("is_refresh",False)   # 不一定存在,默认值设为False

# app.before_request(jwt_authentication)  # 在toutiao/__init__.py中加入


'''
 # 获取请求头中的token
    token = request.headers.get("Authorization")
    if token is not None and token.startswith("Bearer "):
        token = token[7:]
        # 验证token
        payload = verify_jwt(token)

        # 如果payload不为None保存到g对象中
        if payload is not None:
            g.user_id = payload.get("user_id")
            g.is_refresh = payload.get("is_refresh", False)
'''