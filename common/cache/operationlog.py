from models.system import MisOperationLog
from models import db
from flask import current_app, g
from flask_limiter.util import get_remote_address
import traceback


def add_log(operation, description):
    """
    :param operation 操作
    :param description 描述
    :return: None
    """
    try:
        log = MisOperationLog(administrator_id=g.administrator_id,
                              ip=get_remote_address(),
                              operation=operation,
                              description=description)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.error(traceback.format_exc())
        raise ValueError('db error.')
