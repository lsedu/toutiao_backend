from flask_restful import Resource
from flask_limiter.util import get_remote_address
from flask import request, current_app, g, session
from flask_restful.reqparse import RequestParser
from flask_restful import inputs, fields, marshal
from datetime import datetime, timedelta
from sqlalchemy.orm import load_only
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from . import constants
from utils import parser
from models import db
from models.system import MisAdministrator, MisOperationLog
from models.user import *
from utils.jwt_util import generate_jwt
from utils.gt3.geetest import GeetestLib
from cache.permission import get_permission_tree
from utils.decorators import mis_login_required, mis_permission_required
from cache.operationlog import add_log
from utils.storage import upload_image


class UserListResource(Resource):
    """
    用户管理
    """
    user_fields = {
        'user_id': fields.Integer(attribute='id'),  # 用户id
        'account': fields.String(),  # 账号
        'name': fields.String(attribute='name'), # 用户名
        'email': fields.String(),  # 邮箱
        'mobile': fields.String(attribute='mobile'), # 手机号
        'last_login': fields.DateTime(attribute='last_login', dt_format='iso8601'), # 最后活动时间
        'is_verified': fields.Integer(attribute='is_verified'), # 是否实名认证
        'is_media': fields.Integer(attribute='is_media'),  # 是否资质认证
        'status': fields.Integer(attribute='status'), # 状态
    }

    method_decorators = {
        'get': [mis_permission_required('userlist-get')],
        'post': [mis_permission_required('userlist-post')],
        'put': [mis_permission_required('userlist-put')],
    }

    def get(self):
        """
        获取用户列表
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('keyword', location='args')
        args_parser.add_argument('begin', type=parser.date_time, location='args')
        args_parser.add_argument('end', type=parser.date_time, location='args')
        args_parser.add_argument('status', type=inputs.int_range(0, 1), location='args')
        args_parser.add_argument('order_by', location='args')

        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        users = User.query
        if args.keyword:
            users = users.filter(or_(User.mobile.like('%' + args.keyword + '%'),
                                     User.account.like('%' + args.keyword + '%'))
                                 )
        if args.status is not None:
            users = users.filter(User.status == args.status)
        if args.begin and args.end and args.end > args.begin:
            users = users.filter(User.last_login.between(args.begin, args.end))
        if args.order_by is not None:
            if args.order_by == 'id':
                users = users.order_by(User.id.asc())
            else:
                users = users.order_by(User.last_login.desc())
        else:
            users = users.order_by(User.last_login.asc())
        total_count = users.count()
        users = users.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(users, UserListResource.user_fields, envelope='users')
        ret['total_count'] = total_count

        return ret

    def post(self):
        """
        新增用户
        """
        json_parser = RequestParser()
        json_parser.add_argument('account', type=parser.mis_account, required=True, location='json')
        json_parser.add_argument('password', type=parser.mis_password, required=True, location='json')
        json_parser.add_argument('name', type=inputs.regex(r'^.{1,7}$'), required=True, location='json')
        json_parser.add_argument('profile_photo', type=parser.image_base64, required=False, location='json')
        json_parser.add_argument('introduction', required=False, location='json')
        json_parser.add_argument('email', type=parser.email, required=False, location='json')
        json_parser.add_argument('mobile', type=parser.mobile, required=True, location='json')
        json_parser.add_argument('gender', type=inputs.int_range(0, 1), required=True, location='json')
        json_parser.add_argument('area', required=False, location='json')
        json_parser.add_argument('company', required=False, location='json')
        json_parser.add_argument('career', required=False, location='json')
        args = json_parser.parse_args()
        if User.query.filter_by(account=args.account).first():
            return {'message': '{} already exists'.format(args.account)}, 403
        if User.query.filter_by(mobile=args.mobile).first():
            return {'message': '{} already exists'.format(args.mobile)}, 403
        user = User(account=args.account,
                    password=generate_password_hash(args.password),
                    name=args.name,
                    introduction=args.introduction,
                    email=args.email,
                    mobile=args.mobile,
                    status=User.STATUS.ENABLE,
                    last_login=datetime.now()
                    )
        if args.profile_photo:
            try:
                photo_url = upload_image(args.profile_photo)
                user.profile_photo = photo_url
            except Exception as e:
                current_app.logger.error('upload failed {}'.format(e))
                return {'message': 'Uploading profile photo image failed.'}, 507
        db.session.add(user)
        db.session.commit()
        user_profile = UserProfile(id=user.id,
                                   gender=args.gender,
                                   area=args.area,
                                   company=args.company,
                                   career=args.career
                                   )
        db.session.add(user_profile)
        db.session.commit()
        return marshal(user, UserListResource.user_fields), 201

    def put(self):
        """
        批量冻结/解冻
        """
        json_parser = RequestParser()
        json_parser.add_argument('user_ids', action='append', type=inputs.positive,
                                 required=True, location='json')
        json_parser.add_argument('status', type=inputs.int_range(0, 1), required=True, location='json')
        args = json_parser.parse_args()

        count = User.query.filter(User.id.in_(args.user_ids)).update({'status': args.status}, synchronize_session=False)
        db.session.commit()
        return {'count': count}, 201


class UserResource(Resource):
    """
    单用户管理
    """
    method_decorators = {
        'get': [mis_permission_required('user-get')],
    }
    def get(self, target):
        """
        获取用户信息
        """
        user = User.query.filter_by(id=target).first()
        if not user:
            return {'message': 'Invalid user id.'}, 400
        return marshal(user, UserListResource.user_fields)

