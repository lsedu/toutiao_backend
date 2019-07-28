import eventlet
eventlet.monkey_patch()

import socketio
import eventlet.wsgi
import grpc

from im.common import get_config, create_logger

sio = socketio.Server()
rpc_chat = None


def run(port):
    """
    运行
    :param port: 端口
    :return:
    """
    config = get_config()
    log = create_logger(config)

    # rpc
    global rpc_chat
    rpc_chat = grpc.insecure_channel(config.RPC.CHATBOT)

    # create a Socket.IO server
    mgr = socketio.KombuManager(config.RABBITMQ)

    global sio
    sio = socketio.Server(async_mode='eventlet', client_manager=mgr, logger=log, ping_timeout=300)

    sio.JWT_SECRET = config.JWT_SECRET

    # 添加处理
    from . import chatbot, notify

    app = socketio.Middleware(sio)

    eventlet.wsgi.server(eventlet.listen(('', port)), app, log=log)


