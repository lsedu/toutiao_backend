from . import sio
from common import check_user_id_from_querystring


@sio.on('connect')
def on_connect(sid, environ):
    """
    上线时
    :param sid:
    :param environ: WSGI dict
    :return:
    """
    user_id = check_user_id_from_querystring(environ, sio.JWT_SECRET)

    if not user_id:
        return False

    sio.enter_room(sid, str(user_id))


@sio.on('disconnect')
def on_disconnect(sid):
    """
    下线时
    :param sid:
    :return:
    """
    rooms = sio.rooms(sid)
    for room in rooms:
        sio.leave_room(sid, room)
