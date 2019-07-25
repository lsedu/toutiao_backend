from flask import current_app
from sqlalchemy import func

from cache import statistic as cache_statistic
from cache.statistic import UserArticleCountStorage, UserFollowingCountStorage
from models import db
from models.news import Article


def fix_statistic():
    '''
    通过mysql修正redis中的统计数据
    用户文章数量，用户关注数量，用户粉丝数量
    1,查询数据库
    sql: select user_id,count(article_id) from news_article_basic where status=2 group by user_id;
    db.session.query(Article.STATUS==APPROVED).option(loadonly(Article.user_id,func.tool

    2，删除redis 记录

    3，写入redis
    :return:
    '''
    #1,查询数据库
    ret =db.session.filter(Article.STATUS.APPROVED).query(Article.user_id,func.count(Article.id)).group_by(Article.user_id).all()

    #2--调用已经抽离的函数 reset
    UserArticleCountStorage.reset(ret)
    # #2,删除redis记录 key:   count:user:arts
    # redis_cli =current_app.redis_master
    # key ="count:user:arts"
    # redis_cli.delete(key)
    # #3,写入数据
    # """
    #    用户文章数量
    #    键                         值
    #    count:user:article  zset->{   member         score
    #                                user_id_1    3000
    #                                user_id_2    5000
    #                                }
    #     member:user_id,score:count
    #    """
    # #3-1,添加方式一
    # # p1 =redis_cli.pipline()
    # # for user_id,count in ret:
    # #     # redis_cli.zadd(key,score,member)
    # #     redis_cli.zadd(key,count,user_id)
    # # p1.commit() #用管道，全部添加完再提交。缺点：redis在中途崩溃会导致写入失败
    # #3-2添加方式二
    # redis_data_list=[]
    # for user_id,count in ret:
    #     redis_data_list.append(count)
    #     redis_data_list.append(user_id)
    # # 格式：redis_cli.zadd(key score1,member1,score2,member2```)
    # redis_cli.zadd(key,*redis_data_list)  #拆包，批量写入，
    #3--用户关注数量
    ret=db.session.filter(Article.STATUS.APPROVED).query(Article.user_id,func.count()).group_by(Article.user_id).all()
    UserFollowingCountStorage.reset(ret)





# def fix_process(count_storage_cls):
#     #修复处理方法
#     #进行数据库查询
#     ret=count_storage_cls.db_query()
#     #设置redis数据
#     count_storage_cls.reset(ret)


# def fix_statistics(flask_app):
    #修正统计数据
    # with flask_app.app_context():
        # fix_process(cache_statistic.UserArticlesCountStorage)  # 用户文章数量
        # fix_process(cache_statistic.UserFollowingsCountStorage)  #  用户关注数量



# class CountStorageBase(object):
#     """
#     统计数量存储的父类
#     """
#     key=''
#
#     @classmethod
#     def reset(cls, db_query_ret):
#         """
#         由定时任务调用的重置数据方法
#         """
#         # 设置redis的存储记录
#         pl = current_app.redis_master.pipeline()
#         pl.delete(cls.key)
#
#         # zadd(key, score1, val1, score2, val2, ...)
#         # 方式一
#         # for data_id, count in db_query_ret:
#         #     pl.zadd(cls.key, count, data_id)
#
#         # 方式二
#         redis_data = []
#         for data_id, count in db_query_ret:
#             redis_data.append(count)
#             redis_data.append(data_id)
#
#         # redis_data = [count1, data_id1, count2, data_id2, ..]
#         pl.zadd(cls.key, *redis_data)
#         # pl.zadd(cls.key, count1, data_id1, count2, data_id2, ..]
#
#         pl.execute()
#
# class UserArticlesCountStorage(CountStorageBase):
#     """
#     用户文章数量
#     键                         值
#     count:user:article  zset->{   值         score
#                                 user_id_1    3000
#                                 user_id_2    5000
#                                 }
#     """
#     key = 'count:user:arts'
#
#     @staticmethod
#     def db_query():
#         ret = db.session.query(Article.user_id, func.count(Article.id)) \
#             .filter(Article.status == Article.STATUS.APPROVED).group_by(Article.user_id).all()
#         return ret
#
#
# class UserFollowingsCountStorage(CountStorageBase):
#     """
#     用户关注数量
#     """
#     key = 'count:user:followings'
#
#     @staticmethod
#     def db_query():
#         ret = db.session.query(Relation.user_id, func.count(Relation.target_user_id)) \
#             .filter(Relation.relation == Relation.RELATION.FOLLOW)\
#             .group_by(Relation.user_id).all()
#         return ret

