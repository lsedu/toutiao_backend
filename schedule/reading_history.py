###########################
# 已废弃
###########################

import logging
import time

from common import redis_cli, db, toutiao_app


logger = logging.getLogger('apscheduler')


def save_reading_history_to_mysql():
    """
    同步用户阅读历史 from redis to mysql
    """
    r_his = redis_cli['read_his']
    users = r_his.smembers('users')
    if not users:
        return

    pl = r_his.pipeline()
    sql = ''
    for user in users:
        # 取出该用户的浏览历史
        user_id = int(user)
        history = r_his.hgetall('his:{}'.format(user_id))

        # 清除本次处理的浏览历史
        pl.srem('users', user_id)
        pl.delete('his:{}'.format(user_id))
        pl.execute()

        for article_id, timestamp in history.items():
            read_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(timestamp)))
            sql += "INSERT INTO news_read (user_id, article_id, create_time, update_time) VALUES({}, {}, '{}', '{}')" \
                   " ON DUPLICATE KEY UPDATE update_time ='{}';".format(
                        user_id, article_id, read_time, read_time, read_time
                   )

    # 处理浏览历史
    logger.debug(sql)
    with toutiao_app.app_context():
        db.session.execute(sql)
        db.session.commit()

