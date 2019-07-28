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
from models.user import User
from utils.decorators import mis_permission_required


class StatisticsSearchResource(Resource):
    """
    搜索统计
    """
    method_decorators = {
        'get': [mis_permission_required('statistics-search-get')],
    }

    def get(self):
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        ssts = StatisticsSearchTotal.query.order_by(StatisticsSearchTotal.count.desc())
        total_count = ssts.count()

        ret = {
            'keywords':[],
            'total_count': total_count
        }
        ssts = ssts.offset(per_page * (page - 1)).limit(per_page).all()
        for sst in ssts:
            lask_week_count, week_count, week_percent = self._get_week_percent(sst.keyword)
            ret['keywords'].append({
                'keyword': sst.keyword,
                'user_count': sst.user_count,
                'week_percent': week_percent,
                # 'lask_week_count': lask_week_count,
                # 'week_count': week_count
            })

        return ret

    # def post(self):
    #     now = datetime.now()
    #     today = datetime(year=now.year, month=now.month, day=now.day)
    #     begin = today - timedelta(days=14)
    #     while begin <= now:
    #         for word in ['java', 'python', 'php']:
    #             import random
    #             count = user_count = 1
    #             ss = StatisticsSearch.query.filter_by(year=begin.year,
    #                                                     month=begin.month,
    #                                                     day=begin.day,
    #                                                     hour=begin.hour,
    #                                                     keyword=word).first()
    #             if not ss:
    #                 ss = StatisticsSearch(year=begin.year,
    #                                     month=begin.month,
    #                                     day=begin.day,
    #                                     hour=begin.hour,
    #                                     keyword=word,
    #                                     count=0,
    #                                     user_count=0,
    #                                     date_time=datetime(year=begin.year,month=begin.month,
    #                                                         day=begin.day,hour=begin.hour))
    #             sst = StatisticsSearchTotal.query.filter_by(keyword=word).first()
    #             if not sst:
    #                 sst = StatisticsSearchTotal(keyword=word, user_count=0, count=0)
    #             ss.count += count
    #             ss.user_count += user_count
    #             sst.count += count
    #             sst.user_count += user_count
    #             db.session.add(ss)
    #             db.session.add(sst)
    #             db.session.commit()
    #         begin += timedelta(hours=1)
    #     return {}

    def _get_week_percent(self, keyword):
        """
        获取搜索关键字的周涨幅
        :param keyword: 搜索关键字
        :return: 周涨幅百分比
        """
        now = datetime.now()
        today = datetime(year=now.year, month=now.month, day=now.day)

        # 上周用户数量
        lask_week_begin = today - timedelta(days=13)
        lask_week_end = today - timedelta(days=6)
        query = db.session.query(func.sum(StatisticsSearch.user_count)) \
            .filter(StatisticsSearch.keyword == keyword,
                    and_(StatisticsSearch.date_time >= lask_week_begin,
                         StatisticsSearch.date_time < lask_week_end)
                    )
        lask_week_count = int(query.scalar() or 0)

        # 本周用户数量
        week_begin = lask_week_end
        query = db.session.query(func.sum(StatisticsSearch.user_count)) \
            .filter(StatisticsSearch.keyword == keyword,
                    and_(StatisticsSearch.date_time >= week_begin,
                         StatisticsSearch.date_time < now)
                    )
        week_count = int(query.scalar() or 0)

        # 周涨幅
        week_percent = round((week_count - lask_week_count) / (lask_week_count if lask_week_count else 1) * 100, 2)

        return lask_week_count, week_count, week_percent


class StatisticsSearchTotalResource(Resource):
    """
    搜索统计-总数
    """
    method_decorators = {
        'get': [mis_permission_required('statistics-search-total-get')],
    }

    def get(self):
        # 搜索总用户数
        query = db.session.query(func.sum(StatisticsSearchTotal.user_count))
        search_user_count = int(query.scalar() or 0)

        # 总用户数
        query = User.query
        user_count = int(query.count() or 0)

        # 搜索总数
        query = db.session.query(func.sum(StatisticsSearchTotal.count))
        count = int(query.scalar() or 0)
        return {'search_user_count': search_user_count, 'count': count, 'user_count': user_count}


