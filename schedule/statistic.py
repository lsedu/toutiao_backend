# 用于修正redis存储中的统计数据

from common import redis_master, db, toutiao_app
from cache import statistic as cache_statistic


def fix_process(count_storage_cls):
    """
    修复处理方法
    """
    with toutiao_app.app_context():
        db.session().set_to_read()
        ret = count_storage_cls.db_query()
        data = []
        for value, score in ret:
            data.append(score)
            data.append(value)
        count_storage_cls.reset(redis_master, *data)


def fix_statistics():
    """
    修正统计数据
    """
    fix_process(cache_statistic.UserArticlesCountStorage)
    fix_process(cache_statistic.ArticleCollectingCountStorage)
    fix_process(cache_statistic.UserArticleCollectingCountStorage)
    fix_process(cache_statistic.ArticleDislikeCountStorage)
    fix_process(cache_statistic.ArticleLikingCountStorage)
    fix_process(cache_statistic.CommentLikingCountStorage)
    fix_process(cache_statistic.ArticleCommentCountStorage)
    fix_process(cache_statistic.CommentReplyCountStorage)
    fix_process(cache_statistic.UserFollowingsCountStorage)
    fix_process(cache_statistic.UserFollowersCountStorage)
    fix_process(cache_statistic.UserLikedCountStorage)



