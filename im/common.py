import importlib.util
import os
import logging
import logging.handlers
from werkzeug.wrappers import Request

from settings.default import DefaultConfig
from utils import constants
from utils.jwt_util import verify_jwt


def import_from_source(module_name, file_path):
    """
    从文件路径导入模块
    :param module_name: 模块名
    :param file_path: 文件路径
    :return: module
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_config():
    """
    获取配置
    :return: config
    """
    config = DefaultConfig
    config_file = os.environ.get(constants.GLOBAL_SETTING_ENV_NAME)
    if config_file:
        config_module = import_from_source('config', config_file)
        for key in dir(config_module):
            if key.isupper():
                setattr(config, key, getattr(config_module, key))

    return config


def create_logger(config):
    """
    设置日志
    :param config:
    :return:
    """
    # 设置日志
    logging_file_dir = config.LOGGING_FILE_DIR
    logging_file_max_bytes = config.LOGGING_FILE_MAX_BYTES
    logging_file_backup = config.LOGGING_FILE_BACKUP
    logging_level = config.LOGGING_LEVEL

    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logging_file_dir, 'im.log'),
        maxBytes=logging_file_max_bytes,
        backupCount=logging_file_backup
    )
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(module)s %(lineno)d %(message)s'))

    log = logging.getLogger('im')
    log.addHandler(file_handler)
    log.setLevel(logging_level)
    return log


def check_user_id(environ, secret):
    """
    检查用户id
    :param environ:
    :param secret:
    :return: user_id or None
    """
    # 判断用户身份
    request = Request(environ)
    authorization = request.headers.get('Authorization')
    user_id = None
    if authorization and authorization.startswith('Bearer '):
        token = authorization.strip()[7:]
        payload = verify_jwt(token, secret=secret)
        if payload:
            user_id = payload.get('user_id')
    elif authorization and authorization.startswith('Anony '):
        user_id = authorization.strip()[6:]

    return user_id


def check_user_id_from_querystring(environ, secret):
    """
    检查用户id
    :param environ:
    :param secret:
    :return: user_id or None
    """
    # 判断用户身份
    request = Request(environ)
    token = request.args.get('token')
    anonymous = request.args.get('a')

    if token:
        payload = verify_jwt(token, secret=secret)
        if payload:
            user_id = payload.get('user_id')
            return user_id
    elif anonymous:
        return anonymous

    return None
