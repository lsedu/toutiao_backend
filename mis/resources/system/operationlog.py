from flask_restful import Resource
from flask_limiter.util import get_remote_address
from flask import request, current_app, g, session
from flask_restful.reqparse import RequestParser
from flask_restful import inputs, fields, marshal
from datetime import datetime, timedelta
from sqlalchemy.orm import load_only

from . import constants
from utils import parser
from models import db
from models.system import MisAdministrator, MisOperationLog
from utils.jwt_util import generate_jwt
from utils.gt3.geetest import GeetestLib
from cache.permission import get_permission_tree
from utils.decorators import mis_login_required, mis_permission_required
from cache.operationlog import add_log


class OperationLogListResource(Resource):
    """
    运营日记
    """
    logs_fields = {
        'operation_log_id': fields.Integer(attribute='id'),
        'administrator_id': fields.Integer(attribute='administrator_id'),
        'administrator_name': fields.String(attribute='administrator.name'),
        'ip': fields.String(attribute='ip'),
        'operation': fields.String(attribute='operation'),
        'description': fields.String(attribute='description'),
        'ctime': fields.DateTime(attribute='ctime', dt_format='iso8601'),
    }

    method_decorators = {
        'get': [mis_permission_required('operationlog-get')]
    }

    def get(self):
        """
        获取运营日志列表
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('keyword', location='args')
        args_parser.add_argument('order_by', location='args')
        args_parser.add_argument('begin', type=parser.date_time, location='args')
        args_parser.add_argument('end', type=parser.date_time, location='args')
        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        logs = MisOperationLog.query
        if args.keyword:
            logs = logs.filter(MisOperationLog.operation.like('%' + args.keyword + '%'),
                               MisOperationLog.description.like('%' + args.keyword + '%'))
        if args.begin and args.end and args.end > args.begin:
            logs = logs.filter(MisOperationLog.ctime.between(args.begin, args.end))
        if args.order_by is not None:
            if args.order_by == 'id':
                logs = logs.order_by(MisOperationLog.id.desc())
        else:
            logs = logs.order_by(MisOperationLog.ctime.desc())
        total_count = logs.count()
        logs = logs.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(logs, OperationLogListResource.logs_fields, envelope='operationlogs')
        ret['total_count'] = total_count
        add_log('查询', '查询: 运营日志')
        return ret
