import logging
import time
from functools import partial

from . import sio, rpc_chat
from common import check_user_id
from rpc.chatbot import chatbot_pb2, chatbot_pb2_grpc


logger = logging.getLogger('im')


@sio.on('message')
def on_message(sid, data):
    """
    客户端发送消息时
    :param sid:
    :param data:
    :return:
    """
    rooms = sio.rooms(sid)
    assert len(rooms) == 2

    user_id = ''
    for room in rooms:
        if room == sid:
            continue
        else:
            user_id = room
            break

    assert user_id != ''

    # TODO 接入chatbot RPC服务
    stub = chatbot_pb2_grpc.ChatBotServiceStub(rpc_chat)
    timestamp = data.get('timestamp', int(time.time()))
    timestamp = timestamp if timestamp < 10000000000 else int(timestamp/1000)
    req = chatbot_pb2.ReceivedMessage(
        user_id=str(user_id),
        user_message=data.get('msg', ''),
        create_time=timestamp
    )

    # # 同步调用
    # try:
    #     resp = stub.Chatbot(req, timeout=3)
    # except Exception as e:
    #     logger.error(e)
    #     msg = 'oops，我病了，容我缓一下...'
    #     timestamp = int(time.time())
    # else:
    #     msg = resp.user_response
    #     timestamp = resp.create_time
    #
    # sio.send({'msg': msg, 'timestamp': timestamp}, room=sid)

    # 异步调用
    try:
        resp_future = stub.Chatbot.future(req, timeout=3)
        resp_future.add_done_callback(partial(chatbot_rpc_callback, sid=sid))
    except Exception as e:
        logger.error(e)
        msg = 'oops，我病了，容我缓一下...'
        timestamp = int(time.time())
        logger.info('send msg:{} to sid:{}'.format(msg, sid))
        sio.send({'msg': msg, 'timestamp': timestamp}, room=sid)


def chatbot_rpc_callback(resp_future, sid=None):
    try:
        resp = resp_future.result(timeout=3)
    except Exception as e:
        logger.error(e)
        msg = 'oops，我病了，容我缓一下...'
        timestamp = int(time.time())
        logger.info('send msg:{} to sid:{}'.format(msg, sid))
        sio.send({'msg': msg, 'timestamp': timestamp}, room=sid)
    else:
        msg = resp.user_response
        timestamp = resp.create_time
        logger.info('send msg:{} to sid:{}'.format(msg, sid))
        sio.send({'msg': msg, 'timestamp': timestamp}, room=sid)


