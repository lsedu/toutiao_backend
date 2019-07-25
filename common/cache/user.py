import json
from flask import current_app
from redis import RedisError
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import load_only

from cache.constants import UserNotExistsTTL, UserCacheDataTTL
from models.user import User


class UserCache(object):
    '''
    实例属性：在init中定义，每个对象的属性相互独立，互不干扰
    类属性：类属性在每个对象之间共享，全局
    静态方法：

    '''
    def __init__(self,user_id):
        self.key='user:%s:profile'%user_id #实例属性
        self.user_id =user_id

    def get(self):
        '''
        获取用户数据,查询缓存redis集群
        判断redis中是否有记录:
            有
                判断值是否是-1:
                    是  返回None
                    否  返回数据
            无
                查询mysql
                    有  返回并回填(写入redis）
                    无（穿透)  返回None，回填None
        :return:
        '''
        redis_cli=current_app.redis_cluster
        try:
            ret=redis_cli.get(self.key)   #防止redis连接失败时突发情况
        except RedisError as e:
            #记录日志
            current_app.logger.error(e)
            ret =None  #为了能够程序进入mysql查询
        #redis中有记录
        if ret:
            #判断值是否是-1
            if ret == b'-1':
                return None
            else:
                user_dict=json.loads(ret)
                return user_dict
        else:
            #redis无记录，查询mysql
            try:
                user = User.query.option(load_only(
                    User.profile_photo,
                    User.certificate,
                    User.introduction,
                    User.mobile,
                    User.name
                )).filter_by(id=self.user_id).first()
            except DatabaseError as e:
                #记录日志
                current_app.logger.error(e)
                raise e #抛出异常给调用者（视图）
            if user: #flask中ORM查询不到参数会返回None，Django则会报错。if user is not None:
                #查询到，返回数据，存入redis
                user_dict ={
                    "mobile":user.mobile,
                    "name":user.name,
                    "profile_photo":user.profile_photo,
                    "certificate":user.certificate,
                    "introduction":user.introduction
                }
                redis_cli.setex(self.key,UserCacheDataTTL.get_value(),json.dumps(user_dict))
                return user_dict
            else:
                # 查询不到，返回None 穿透
                try:
                    redis_cli.setex(self.key,UserNotExistsTTL.get_value(),"-1")
                except RedisError as e:
                    current_app.logger.error(e)
                return None

    def clear(self): #delete
        '''
        删除某一个键 "user:{}:profile".format(user_id)
        :return:
        '''
        try:
            redis_cli=current_app.redis_cluster
            redis_cli.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)

    def datemine_user_exists(self):
        '''
        通过缓存来判断用户是否存在
            有记录
                是否是 -1
                    是 返回 False
                    否 返回 True
            无记录
                在mysql中查询，是否有记录
                    有 返回True （回填）
                    无 （穿透)返回Flase  回填‘-1’ (redis)

        :return:
        '''
        ret =self.get() #调用上面的get方法
        if ret:
            return True
        else:
            return False