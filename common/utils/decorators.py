from flask import g, current_app
from functools import wraps
from sqlalchemy.orm import load_only
from sqlalchemy.exc import SQLAlchemyError


from models import db


def set_db_to_read(func):
    """
    设置使用读数据库
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        db.session().set_to_read()
        return func(*args, **kwargs)
    return wrapper


def set_db_to_write(func):
    """
    设置使用写数据库
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        db.session().set_to_write()
        return func(*args, **kwargs)
    return wrapper


def login_required(func):

    def wrapper(*args, **kwargs):

        # 判断g.user_id不为空，并且 g.is_refresh 是False
        if g.user_id is not None and g.is_refresh is False:
            # 说明此次请求获取到用户的id，获取到的is_refresh是False，即此次请求不是为了刷新token
            # 就可以正常执行视图了
            return func(*args, **kwargs)
        else:
            return {"message": "Invalid token"}, 401
    return wrapper