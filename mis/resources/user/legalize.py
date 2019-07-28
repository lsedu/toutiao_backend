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


class LegalizeListResource(Resource):
    """
    用户认证申请记录
    """
    legalize_fields = {
        'legalize_id': fields.Integer(attribute='id'), # 申请记录id
        'account': fields.String(attribute='user.account'),  # 账号
        'name': fields.String(attribute='user.name'), # 用户名
        'create_time': fields.DateTime(attribute='ctime', dt_format='iso8601'), # 申请认证时间
        'type': fields.Integer(attribute='type'), # 认证类型
        'status': fields.Integer(attribute='status'), # 状态
    }

    method_decorators = {
        'get': [mis_permission_required('legalize-list-get')],
        'post': [mis_permission_required('legalize-list-post')],
        'put': [mis_permission_required('legalize-list-put')],
    }

    def get(self):
        """
        获取用户认证申请记录
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('status', type=inputs.positive, location='args')
        args_parser.add_argument('order_by', location='args')

        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        legalizes = LegalizeLog.query
        if args.status is not None:
            legalizes = legalizes.filter_by(status=args.status)
        if args.order_by is not None:
            if args.order_by == 'id':
                legalizes = legalizes.order_by(LegalizeLog.id.asc())
            else:
                legalizes = legalizes.order_by(LegalizeLog.utime.desc())
        else:
            legalizes = legalizes.order_by(LegalizeLog.utime.desc())
        total_count = legalizes.count()
        legalizes = legalizes.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(legalizes, LegalizeListResource.legalize_fields, envelope='legalizes')
        ret['total_count'] = total_count

        return ret

    def post(self):
        """
        *** 测试
        """
        user_id = 8
        # qual = Qualification(user_id=user_id,
        #                      name='wangzq',
        #                      id_number='440982199006091854',
        #                      industry='软件',
        #                      company='cz',
        #                      position='python',
        #                      add_info='nothing',
        #                      id_card_front='id_card_front',
        #                      id_card_back='id_card_back',
        #                      id_card_handheld='id_card_handheld',
        #                      qualification_img='qualification_img',
        #             )
        # db.session.add(qual)
        # db.session.commit()
        legal = LegalizeLog(
            user_id=user_id,
            type=LegalizeLog.TYPE.REAL_NAME,
            status=LegalizeLog.STATUS.PROCESSING
        )
        db.session.add(legal)
        db.session.commit()

        return marshal(legal, LegalizeListResource.legalize_fields), 201

    def put(self):
        """
        批量通过/驳回
        """
        json_parser = RequestParser()
        json_parser.add_argument('legalize_ids', action='append', type=inputs.positive,
                                 required=True, location='json')
        json_parser.add_argument('status', type=inputs.int_range(2, 3), required=True, location='json')
        json_parser.add_argument('reject_reason', location='json')
        args = json_parser.parse_args()

        legalizes = LegalizeLog.query.filter(LegalizeLog.id.in_(args.legalize_ids))
        user_ids = [legal.user_id for legal in legalizes.all()]
        count = legalizes.update({'status': args.status}, synchronize_session=False)
        if args.status == LegalizeLog.STATUS.REJECT:
            legalizes.update({'reject_reason': args.reject_reason or '资料不通过，驳回'}, synchronize_session=False)
            User.query.filter(User.id.in_(user_ids)).update({'is_media': False}, synchronize_session=False)
        elif args.status == LegalizeLog.STATUS.APPROVED:
            User.query.filter(User.id.in_(user_ids)).update({'is_media': True}, synchronize_session=False)

        db.session.commit()
        return {'count': count}, 201


class LegalizeResource(Resource):
    method_decorators = {
        'get': [mis_permission_required('legalize-get')],
    }

    def get(self, target):
        """
        用户认证申请记录-详细信息
        """
        legal = LegalizeLog.query.filter_by(id=target).first()
        if not legal:
            return {'message': 'Invalid legalize id.'}, 400
        ret = marshal(legal, LegalizeListResource.legalize_fields)
        if legal.type == LegalizeLog.TYPE.REAL_NAME:
            up = UserProfile.query.filter_by(id=legal.user_id).first()
            ret['user_profile'] = dict(user_id=up.id,
                                       gender=up.gender,
                                       birthday=up.birthday.strftime('%Y-%m-%d') if up.birthday else '',
                                       real_name=up.real_name,
                                       id_number=up.id_number,
                                       id_card_front=up.id_card_front,
                                       id_card_back=up.id_card_back,
                                       id_card_handheld=up.id_card_handheld,
                                       area=up.area,
                                       company=up.company,
                                       career=up.career)
        elif legal.type == LegalizeLog.TYPE.QUALIFICATION:
            qa = legal.qualification
            ret['qualification'] = dict(qualification_id=qa.id,
                                        user_id=qa.user_id,
                                        name=qa.name,
                                        id_number=qa.id_number,
                                        industry=qa.industry,
                                        company=qa.company,
                                        position=qa.position,
                                        add_info=qa.add_info,
                                        id_card_front=qa.id_card_front,
                                        id_card_back=qa.id_card_back,
                                        id_card_handheld=qa.id_card_handheld,
                                        qualification_img=qa.qualification_img)
        return ret


