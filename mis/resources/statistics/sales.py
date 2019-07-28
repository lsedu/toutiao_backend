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


class StatisticsSalesTotalResource(Resource):
    """
    销售额统计-总数
    """
    method_decorators = {
        'get': [mis_permission_required('statistics-sales-total-get')],
    }

    def get(self):
        """
        地区销售额排行榜
        :return:
        """
        ssts = StatisticsSalesTotal.query.order_by(StatisticsSalesTotal.money.desc()).all()
        ret = {
            'area_sales': [],
            'total_money':0
        }

        for sst in ssts:
            ret['total_money'] += sst.money
            ret['area_sales'].append(dict(area=sst.area,
                                          area_name=StatisticsArea.area_map[sst.area],
                                          money=sst.money))

        return ret

    def post(self):
        for area in StatisticsArea.area_map:
            import random
            money = random.randint(100, 1000) * 100
            sst = StatisticsSalesTotal.query.filter_by(area=area).first()
            if not sst:
                sst = StatisticsSalesTotal(area=area, money=0)

            sst.money += money
            db.session.add(sst)
            db.session.commit()
        return {}


