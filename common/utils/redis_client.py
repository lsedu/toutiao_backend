from redis import StrictRedis


def create_redis_clients(flask_app):
    """
    创建redis客户端
    :param flask_app: Flask应用对象
    :return: dict redis客户端对象的字典
    """
    return {
        'sms_code': StrictRedis.from_url(flask_app.config['REDIS'].SMS_CODE),
        'read_his': StrictRedis.from_url(flask_app.config['REDIS'].READING_HISTORY, decode_responses=True),
        'art_cache': StrictRedis.from_url(flask_app.config['REDIS'].ARTICLE_CACHE),
        'user_cache': StrictRedis.from_url(flask_app.config['REDIS'].USER_CACHE, decode_responses=True),
        'comm_cache': StrictRedis.from_url(flask_app.config['REDIS'].COMMENT_CACHE, decode_responses=True),
        'notice_cache': StrictRedis.from_url(flask_app.config['REDIS'].NOTICE_CACHE),
    }
