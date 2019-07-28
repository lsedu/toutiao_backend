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


class StatisticsBasicResource(Resource):
    """
    基本统计
    """
    method_decorators = {
        'get': [mis_permission_required('statistics-basic-get')],
    }

    def _get_size_hour(self, statistics_type, args):
        # 获取粒度为小时的数据
        ret = []
        begin = args.begin
        while begin <= args.end + timedelta(hours=23):
            query = db.session.query(func.sum(StatisticsBasic.count)) \
                .filter(StatisticsBasic.type == statistics_type,
                        and_(StatisticsBasic.date_time >= begin,
                             StatisticsBasic.date_time < begin + timedelta(hours=1))
                        )
            hour_count = int(query.scalar() or 0)
            ret.append(dict(date_time=begin.strftime('%Y-%m-%d %H:%M:%S'), count=hour_count))
            begin += timedelta(hours=1)
        return ret

    def _get_size_day(self, statistics_type, args):
        # 获取粒度为天的数据
        ret = []
        begin = args.begin
        while begin <= args.end:
            query = db.session.query(func.sum(StatisticsBasic.count)) \
                .filter(StatisticsBasic.type == statistics_type,
                        and_(StatisticsBasic.date_time >= begin,
                             StatisticsBasic.date_time < begin + timedelta(days=1))
                        )
            day_count = int(query.scalar() or 0)
            ret.append(dict(date=begin.strftime('%Y-%m-%d'), count=day_count))
            begin += timedelta(days=1)
        return ret

    def _get_size_month(self, statistics_type):
        # 获取粒度为月的全年数据
        ret = []
        now = datetime.now()
        month = 1
        while True:
            if month > 12:
                break
            begin = datetime(now.year, month=month, day=1)
            if month == 12:
                end = datetime(now.year + 1, month=1, day=1)
            else:
                end = datetime(now.year, month=month + 1, day=1)
            query = db.session.query(func.sum(StatisticsBasic.count)) \
                .filter(StatisticsBasic.type == statistics_type,
                        and_(StatisticsBasic.date_time >= begin,
                             StatisticsBasic.date_time < end)
                        )
            month_count = int(query.scalar() or 0)
            ret.append(dict(month=month, count=month_count))
            month += 1
        return ret

    def get(self):
        args_parser = RequestParser()
        args_parser.add_argument('type', type=parser.statistics_type, required=True, location='args')
        args_parser.add_argument('size', type=parser.statistics_size, location='args')
        args_parser.add_argument('begin', type=parser.date, location='args')
        args_parser.add_argument('end', type=parser.date, location='args')
        args = args_parser.parse_args()
        statistics_type = StatisticsType.type_map[args.type]
        if args.size is not None:
            # 不同粒度的图表数据
            if args.size == 'month':
                return self._get_size_month(statistics_type)
            elif args.size == 'day':
                if not args.begin or not args.end or args.begin > args.end:
                    return {'message': '(begin or end) parameter error.'}, 403
                return self._get_size_day(statistics_type, args)
            elif args.size == 'hour':
                if not args.begin or not args.end or args.begin > args.end:
                    return {'message': '(begin or end) parameter error.'}, 403
                return self._get_size_hour(statistics_type, args)
        else:
            # 获取基本统计数据
            # 1.当天总数 2.周涨/降幅百分比 3.日涨/降幅百分比 4.日平均数 5.总天数 6.总数量

            now = datetime.now()
            today = datetime(year=now.year, month=now.month, day=now.day)

            # 总数
            query = db.session.query(func.sum(StatisticsBasic.count)) \
                .filter(StatisticsBasic.type == statistics_type)
            total_count = int(query.scalar() or 0)

            # 总天数
            first_day = StatisticsBasic.query.order_by(StatisticsBasic.date_time.asc()).first()
            total_days = 0
            if first_day is not None:
                total_days = (now - first_day.date_time).days
                if (now - first_day.date_time).seconds > total_days * 3600 * 24:
                    total_days += 1

            # 当天总数
            query = db.session.query(func.sum(StatisticsBasic.count))\
                .filter(StatisticsBasic.type == statistics_type,
                        StatisticsBasic.date_time.between(today, now)
                        )
            day_count = int(query.scalar() or 0)

            # 昨天总数
            yesterday = today - timedelta(days=1)
            query = db.session.query(func.sum(StatisticsBasic.count))\
                .filter(StatisticsBasic.type==statistics_type,
                        and_(StatisticsBasic.date_time >= yesterday,
                             StatisticsBasic.date_time < today)
                        )
            yesterday_count = int(query.scalar() or 0)

            # 上周数量
            lask_week_begin = today - timedelta(days=13)
            lask_week_end = today - timedelta(days=6)
            query = db.session.query(func.sum(StatisticsBasic.count))\
                .filter(StatisticsBasic.type==statistics_type,
                        and_(StatisticsBasic.date_time >= lask_week_begin,
                             StatisticsBasic.date_time < lask_week_end)
                        )
            lask_week_count = int(query.scalar() or 0)

            # 本周数量
            week_begin = lask_week_end
            query = db.session.query(func.sum(StatisticsBasic.count)) \
                .filter(StatisticsBasic.type == statistics_type,
                        and_(StatisticsBasic.date_time >= week_begin,
                             StatisticsBasic.date_time < now)
                        )
            week_count = int(query.scalar() or 0)

            # 周同比
            week_percent = round((week_count - lask_week_count) / (lask_week_count if lask_week_count else 1) * 100, 2)
            # 日环比
            day_percent = round((day_count - yesterday_count) / (yesterday_count if yesterday_count else 1) * 100, 2)
            # 日均数
            day_average = round(total_count / (total_days if total_days else 1), 2)

            ret = dict(day_count=day_count,
                       week_percent=week_percent,
                       day_percent=day_percent,
                       day_average=day_average,
                       total_days=total_days,
                       total_count=total_count)
            return ret

    # def post(self):
    #     now = datetime.now()
    #     today = datetime(year=now.year, month=now.month, day=now.day)
    #     begin = today - timedelta(days=14)
    #     while begin <= now:
    #         sb = StatisticsBasic.query.filter_by(year=begin.year,
    #                                             month=begin.month,
    #                                             day=begin.day,
    #                                             hour=begin.hour,
    #                                             type=StatisticsType.DAY_ACTIVATE).first()
    #         if not sb:
    #             sb = StatisticsBasic(year=begin.year,
    #                                             month=begin.month,
    #                                             day=begin.day,
    #                                             hour=begin.hour,
    #                                             type=StatisticsType.DAY_ACTIVATE,
    #                                             count=1,
    #                                             date_time=datetime(year=begin.year,month=begin.month,
    #                                                                 day=begin.day,hour=begin.hour))
    #             db.session.add(sb)
    #             db.session.commit()
    #         print(begin)
    #         begin += timedelta(hours=1)
    #     return {}

