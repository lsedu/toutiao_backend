import os
import logging.handlers
from redis.sentinel import Sentinel

from toutiao import create_flask_app
from settings.default import DefaultConfig
from models import db

toutiao_app = create_flask_app(DefaultConfig, enable_config_file=True)
db.init_app(toutiao_app)

_sentinel = Sentinel(toutiao_app.config['REDIS_SENTINELS'])
redis_master = _sentinel.master_for(toutiao_app.config['REDIS_SENTINEL_SERVICE_NAME'])


def create_logger():
    # 设置日志
    logging_file_dir = toutiao_app.config['LOGGING_FILE_DIR']
    logging_file_max_bytes = toutiao_app.config['LOGGING_FILE_MAX_BYTES']
    logging_file_backup = toutiao_app.config['LOGGING_FILE_BACKUP']
    logging_level = toutiao_app.config['LOGGING_LEVEL']

    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logging_file_dir, 'aps_offline.log'),
        maxBytes=logging_file_max_bytes,
        backupCount=logging_file_backup
    )
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(module)s %(lineno)d %(message)s'))

    log = logging.getLogger('apscheduler')
    log.addHandler(file_handler)
    log.setLevel(logging_level)
