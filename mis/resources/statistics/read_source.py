from flask_restful import Resource
from flask import request, current_app, g, session
from flask_restful.reqparse import RequestParser
from flask_restful import inputs, fields, marshal
from datetime import datetime, timedelta, date
from sqlalchemy.orm import load_only
from sqlalchemy import or_, func, and_

from . import constants
from utils import parser
from models import db
from models.statistics import *
from utils.decorators import mis_permission_required


class StatisticsReadSourceTotalResource(Resource):
    """
    阅读来源统计-总数
    """
    method_decorators = {
        'get': [mis_permission_required('statistics-read-source-total-get')],
    }

    def get(self):
        srsts = StatisticsReadSourceTotal.query.order_by(StatisticsReadSourceTotal.count.desc()).all()
        ret = {
            'read_sources': [],
            'total_read_count': 0
        }
        for srst in srsts:
            ret['total_read_count'] += srst.count
            ret['read_sources'].append({
                'source': srst.source,
                'source_name': StatisticsReadSourceTotal.SOURCE.source_map[srst.source],
                'count': srst.count,
                'count_20_down': srst.count_20_down,
                'count_20_80': srst.count_20_80,
                'count_80_up': srst.count_80_up,
            })

        return ret


    def post(self):
        for source in StatisticsReadSourceTotal.SOURCE.source_map:
            srst = StatisticsReadSourceTotal.query.filter_by(source=source).first()
            if not srst:
                srst = StatisticsReadSourceTotal(source=source, count=3, count_20_down=1, count_20_80=1, count_80_up=1)

            db.session.add(srst)
            db.session.commit()

        return {}
