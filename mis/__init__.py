from flask import Flask
from elasticsearch5 import Elasticsearch
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from flask_cors import *
from kafka import KafkaProducer


def create_flask_app(config, enable_config_file=False):
    """
    创建Flask应用
    :param config: 配置信息对象
    :param enable_config_file: 是否允许运行环境中的配置文件覆盖已加载的配置信息
    :return: Flask应用
    """
    app = Flask(__name__)
    app.config.from_object(config)
    if enable_config_file:
        from utils import constants
        app.config.from_envvar(constants.GLOBAL_SETTING_ENV_NAME, silent=True)

    return app


def create_app(config, enable_config_file=False):
    """
    创建应用
    :param config: 配置信息对象
    :param enable_config_file: 是否允许运行环境中的配置文件覆盖已加载的配置信息
    :return: 应用
    """
    app = create_flask_app(config, enable_config_file)
    # 允许跨域
    CORS(app, supports_credentials=True)
    # 限流器
    from utils.limiter import limiter
    limiter.init_app(app)

    # 配置日志
    from utils.logging import create_logger
    create_logger(app)

    # 注册url转换器
    from utils.converters import register_converters
    register_converters(app)

    # redis
    # 暂时保留旧redis接口
    from utils.redis_client import create_redis_clients
    app.redis_cli = create_redis_clients(app)

    from redis.sentinel import Sentinel
    _sentinel = Sentinel(app.config['REDIS_SENTINELS'])
    app.redis_master = _sentinel.master_for(app.config['REDIS_SENTINEL_SERVICE_NAME'])
    app.redis_slave = _sentinel.slave_for(app.config['REDIS_SENTINEL_SERVICE_NAME'])

    from rediscluster import StrictRedisCluster
    app.redis_cluster = StrictRedisCluster(startup_nodes=app.config['REDIS_CLUSTER'])

    # rpc
    # app.rpc_reco = grpc.insecure_channel(app.config['RPC'].RECOMMEND)

    # Elasticsearch
    app.es = Elasticsearch(
        app.config['ES'],
        # sniff before doing anything
        sniff_on_start=True,
        # refresh nodes after a node fails to respond
        sniff_on_connection_fail=True,
        # and also every 60 seconds
        sniffer_timeout=60
    )

    # socket.io
    # app.sio = socketio.KombuManager(app.config['RABBITMQ'], write_only=True)

    # 与推荐系统对接的kafka
    app.kafka_producer = KafkaProducer(bootstrap_servers=app.config['KAFKA_SERVERS'])

    # MySQL数据库连接初始化
    from models import db

    db.init_app(app)

    # 已废弃 添加异常处理
    # from utils.error_handlers import handle_redis_error, handler_mysql_error
    # app.register_error_handler(RedisError, handle_redis_error)
    # app.register_error_handler(SQLAlchemyError, handler_mysql_error)

    # 添加请求钩子
    from utils.middlewares import mis_jwt_authentication
    app.before_request(mis_jwt_authentication)

    # 注册用户管理模块蓝图
    from .resources.user import user_bp
    app.register_blueprint(user_bp)

    # 注册信息管理模块蓝图
    from .resources.information import information_bp
    app.register_blueprint(information_bp)

    # 注册数据统计模块蓝图
    from .resources.statistics import statistics_bp
    app.register_blueprint(statistics_bp)

    # 注册系统管理模块蓝图
    from .resources.system import system_bp
    app.register_blueprint(system_bp)

    # 注册推荐系统模块蓝图
    from .resources.recommend import recommend_bp
    app.register_blueprint(recommend_bp)

    return app

