import socketio
from datetime import datetime, timedelta
import time


import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))

from utils.jwt_util import generate_jwt
from im.common import get_config


sio = socketio.Client()


CHATBOOT_NS = '/chatbot'


@sio.on('connect', namespace=CHATBOOT_NS)
def on_connect():
    print('connected')
    msg = input('Say:')
    sio.send({'msg': msg, 'timestamp': int(time.time())}, namespace=CHATBOOT_NS)


@sio.on('message', namespace=CHATBOOT_NS)
def on_message(data):
    print('I received: {}'.format(data))
    msg = input('Say:')
    sio.send({'msg': msg, 'timestamp': int(time.time())}, namespace=CHATBOOT_NS)


# 获取配置信息
config = get_config()

# 颁发JWT
now = datetime.utcnow()
expiry = now + timedelta(hours=2)
token = generate_jwt({'user_id': 1, 'refresh': False}, expiry, secret=config.JWT_SECRET)

sio.connect('http://127.0.0.1:8003',
            socketio_path='im',
            headers={'Authorization': 'Bearer {}'.format(token)},
            namespaces=[CHATBOOT_NS])
sio.wait()
