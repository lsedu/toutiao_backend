################################
#          已废弃
################################

from common import redis_cli

USER_CACHE_LIMIT = 10000
USER_FOLLOWING_CACHE_LIMIT = 10000
USER_FANS_CACHE_LIMIT = 10000
USER_ARTICLE_CACHE_LIMIT = 10000


ARTICLE_COMMENT_CACHE_LIMIT = 10000  # 热门评论的文章缓存数量
COMMENT_REPLY_CACHE_LIMIT = 10000  # 热门回复的评论缓存数量
COMMENT_CONTENT_CACHE_LIMIT = 100  # 评论的缓存限制

ARTICLE_CACHE_LIMIT = 50000


def clear_user_cache():
    """
    清理用户数据缓存，仅保留有限的最近活跃用户
    """
    r = redis_cli['user_cache']
    size = r.zcard('user')
    if size <= USER_CACHE_LIMIT:
        return

    end_index = size - USER_CACHE_LIMIT
    user_id_li = r.zrange('user', 0, end_index-1)
    user_cache_keys = []
    for user_id in user_id_li:
        user_cache_keys.append('user:{}'.format(user_id))
    pl = r.pipeline()
    pl.delete(*user_cache_keys)
    pl.zrem('user', *user_id_li)
    pl.execute()


def clear_user_following_cache():
    """
    清理用户关注数据
    """
    r = redis_cli['user_cache']
    size = r.zcard('user:following')
    if size <= USER_FOLLOWING_CACHE_LIMIT:
        return

    end_index = size - USER_FOLLOWING_CACHE_LIMIT
    user_id_li = r.zrange('user:following', 0, end_index - 1)
    user_cache_keys = []
    for user_id in user_id_li:
        user_cache_keys.append('user:{}:following'.format(user_id))
    pl = r.pipeline()
    pl.delete(*user_cache_keys)
    pl.zrem('user:following', *user_id_li)
    pl.execute()


def clear_user_fans_cache():
    """
    清理用户粉丝数据
    """
    r = redis_cli['user_cache']
    size = r.zcard('user:fans')
    if size <= USER_FANS_CACHE_LIMIT:
        return

    end_index = size - USER_FANS_CACHE_LIMIT
    user_id_li = r.zrange('user:fans', 0, end_index - 1)
    user_cache_keys = []
    for user_id in user_id_li:
        user_cache_keys.append('user:{}:fans'.format(user_id))
    pl = r.pipeline()
    pl.delete(*user_cache_keys)
    pl.zrem('user:fans', *user_id_li)
    pl.execute()


def clear_user_article_cache():
    """
    清理用户文章数据
    """
    r = redis_cli['user_cache']
    size = r.zcard('user:art')
    if size <= USER_ARTICLE_CACHE_LIMIT:
        return

    end_index = size - USER_ARTICLE_CACHE_LIMIT
    user_id_li = r.zrange('user:art', 0, end_index - 1)
    user_cache_keys = []
    for user_id in user_id_li:
        user_cache_keys.append('user:{}:art'.format(user_id))
    pl = r.pipeline()
    pl.delete(*user_cache_keys)
    pl.zrem('user:art', *user_id_li)
    pl.execute()


def clear_comment_cache():
    """
    清理评论（包括评论回复）的缓存，仅保留有限的最热评论数据
    """
    r = redis_cli['comm_cache']
    pl = r.pipeline()

    # 清理文章评论
    size = r.zcard('art:comm')

    # 清理非热门评论
    if size > ARTICLE_COMMENT_CACHE_LIMIT:
        end_index = size - ARTICLE_COMMENT_CACHE_LIMIT
        article_id_li = r.zrange('art:comm', 0, end_index-1)
        delete_keys = []
        if article_id_li:
            for article_id in article_id_li:

                comment_id_li = r.zrange('art:{}:comm'.format(article_id), 0, -1)
                if comment_id_li:
                    for comment_id in comment_id_li:
                        delete_keys.append('comm:{}'.format(comment_id))

                delete_keys.append('art:{}:comm'.format(article_id))
                delete_keys.append('art:{}:comm:figure'.format(article_id))

            if delete_keys:
                pl.delete(*delete_keys)
            pl.zrem('art:comm', *article_id_li)
            pl.execute()

    # 清理热门评论数量
    delete_keys = []
    article_id_li = r.zrange('art:comm', 0, -1)
    if article_id_li:
        for article_id in article_id_li:
            size = r.zcard('art:{}:comm'.format(article_id))
            if size > COMMENT_CONTENT_CACHE_LIMIT:
                end_index = size - ARTICLE_COMMENT_CACHE_LIMIT
                comment_id_li = r.zrange('art:{}:comm'.format(article_id), 0, end_index - 1)
                if comment_id_li:
                    for comment_id in comment_id_li:
                        delete_keys.append('comm:{}'.format(comment_id))
    if delete_keys:
        r.delete(*delete_keys)

    # 清理评论回复
    size = r.zcard('comm:reply')

    # 清理非热门评论回复
    if size > COMMENT_REPLY_CACHE_LIMIT:
        end_index = size - COMMENT_REPLY_CACHE_LIMIT
        comment_id_li = r.zrange('comm:reply', 0, end_index-1)
        delete_keys = []
        if comment_id_li:
            for comment_id in comment_id_li:

                reply_id_li = r.zrange('comm:{}:reply'.format(comment_id), 0, -1)
                if reply_id_li:
                    for reply_id in reply_id_li:
                        delete_keys.append('comm:{}'.format(reply_id))

                delete_keys.append('comm:{}:reply'.format(comment_id))
                delete_keys.append('comm:{}:reply:figure'.format(comment_id))

            if delete_keys:
                pl.delete(*delete_keys)

            pl.zrem('comm:reply', *comment_id_li)
            pl.execute()

    # 清理热门评论回复数量
    delete_keys = []
    comment_id_li = r.zrange('comm:reply', 0, -1)
    if comment_id_li:
        for comment_id in comment_id_li:
            size = r.zcard('comm:{}:reply'.format(comment_id))
            if size > COMMENT_CONTENT_CACHE_LIMIT:
                end_index = size - ARTICLE_COMMENT_CACHE_LIMIT
                reply_id_li = r.zrange('comm:{}:reply'.format(comment_id), 0, end_index - 1)
                if reply_id_li:
                    for reply_id in reply_id_li:
                        delete_keys.append('comm:{}'.format(reply_id))
    if delete_keys:
        r.delete(*delete_keys)


def clear_article_cache():
    """
    清理文章缓存
    """
    r = redis_cli['art_cache']
    size = r.zcard('art')
    if size <= ARTICLE_CACHE_LIMIT:
        return

    end_index = size - ARTICLE_CACHE_LIMIT
    article_id_li = r.zrange('art', 0, end_index - 1)
    article_cache_keys = []
    for article_id in article_id_li:
        article_cache_keys.append('art:{}:info'.format(article_id.decode()))
        # TODO 清理文章detail缓存
    pl = r.pipeline()
    pl.delete(*article_cache_keys)
    pl.zrem('art', *article_id_li)
    pl.execute()



