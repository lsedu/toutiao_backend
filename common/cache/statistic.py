from flask import current_app
from sqlalchemy import func
from models import db
from models.news import Article
from models.user import Relation


class CountStorageBase(object):
    """
       用户文章数量
       键                         值
       count:user:article  zset->{   值         score
                                   user_id_1    3000
                                   user_id_2    5000
                                   }
       """
    # key ='count:user:arts'
    key =''
    @classmethod
    def get(cls,user_id):
        """
           查询redis记录
                如果redis存在
                    返回
                不存在就返回0 表示用户没发布过文章
           """
        try:
            count = current_app.redis_master.zscore(cls.key,user_id)
        except ConnectionError as e:
            #redis_master连接不上时连接redis_slave并且记入日志
            current_app.logger.error(e)
            count = current_app.redis_slave.zscore(cls.key,user_id)
        if count:
            return int(count)
        else:
            return 0

    @classmethod
    def incr(cls,user_id,incr_num=1):
        """
           用于增加用户的文章数量
           """
        try:
            current_app.redis_master.zincrby(cls.key,user_id,incr_num)
        except ConnectionError as e:
            current_app.logger.error(e)
            raise e #redis_master查询不到时直接报错

    @classmethod
    def reset(cls,query_result): #query_result查询结果
        # 2,删除redis记录 key:   count:user:arts
        redis_cli = current_app.redis_master
        # key = "count:user:arts"
        key=cls.key
        redis_cli.delete(key)
        # 3,写入数据
        """
           用户文章数量
           键                         值
           count:user:article  zset->{   member         score
                                       user_id_1    3000
                                       user_id_2    5000
                                       }
            member:user_id,score:count
           """
        # 3-1,添加方式一
        # p1 =redis_cli.pipline()
        # for user_id,count in ret:
        #     # redis_cli.zadd(key,score,member)
        #     redis_cli.zadd(key,count,user_id)
        # p1.commit() #用管道，全部添加完再提交。缺点：redis在中途崩溃会导致写入失败
        # 3-2添加方式二
        redis_data_list = []
        for user_id, count in query_result:
            redis_data_list.append(count)
            redis_data_list.append(user_id)
        # 格式：redis_cli.zadd(key score1,member1,score2,member2```)
        redis_cli.zadd(key, *redis_data_list)  # 拆包，批量写入，

class UserArticleCountStorage(CountStorageBase):
    key = 'count:user:arts'


class UserFollowingCountStorage(CountStorageBase):
    key = 'count:user:followings'

class UserFansCountStorage(CountStorageBase):
    key = 'count:user:fans'


