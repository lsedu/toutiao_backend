import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ProcessPoolExecutor

from schedule.common import create_logger


# 创建scheduler，多进程执行
executors = {
    'default': ProcessPoolExecutor(3)
}

scheduler = BlockingScheduler(executors=executors)

create_logger()

# 添加离线任务
# 阅读历史已废弃定时同步到mysql数据库方案
# from reading_history import save_reading_history_to_mysql
# scheduler.add_job(save_reading_history_to_mysql, trigger='interval', minutes=10)

# 已废弃
# from clear_cache import clear_user_cache, clear_comment_cache, clear_article_cache
# from clear_cache import clear_user_following_cache, clear_user_fans_cache, clear_user_article_cache
# scheduler.add_job(clear_user_cache, trigger='interval', minutes=10)
# scheduler.add_job(clear_comment_cache, trigger='interval', minutes=10)
# scheduler.add_job(clear_article_cache, trigger='interval', minutes=10)
# scheduler.add_job(clear_user_following_cache, trigger='interval', minutes=10)
# scheduler.add_job(clear_user_fans_cache, trigger='interval', minutes=10)
# scheduler.add_job(clear_user_article_cache, trigger='interval', minutes=10)

# 用于生成测试数据的cover图片
# from cover import generate_article_cover
# scheduler.add_job(generate_article_cover, trigger='date')

# 修正统计数据
from statistic import fix_statistics
scheduler.add_job(fix_statistics, trigger='cron', hour=3)

scheduler.start()


