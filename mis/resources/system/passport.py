from flask_restful import Resource, original_flask_make_response
from werkzeug.security import check_password_hash, generate_password_hash
from flask_limiter.util import get_remote_address
from flask import request, current_app, g, session, make_response
from flask_restful.reqparse import RequestParser
from datetime import datetime, timedelta
from sqlalchemy.orm import load_only

from . import constants
from utils import parser
from models import db
from models.system import MisAdministrator
from utils.jwt_util import generate_jwt
from utils.gt3.geetest import GeetestLib
from cache.permission import get_permission_tree
from utils.decorators import mis_login_required


class CaptchaResource(Resource):
    """
    验证码
    """
    def get(self, account):
        """
        获取验证码
        """
        gt = GeetestLib(current_app.config['GEETEST_ID'], current_app.config['GEETEST_KEY'])
        status = gt.pre_process(account)
        session[gt.GT_STATUS_SESSION_KEY] = status
        session['account'] = account
        response_str = gt.get_response_str()
        # resp = original_flask_make_response(response_str)
        # resp.set_cookie('account', account)
        return response_str


class AuthorizationResource(Resource):
    """
    认证
    """

    def _generate_tokens(self, administrator_id, with_refresh_token=True):
        """
        生成token 和refresh_token
        :param administrator_id: 管理员id
        :return: token, refresh_token
        """
        # 颁发JWT
        now = datetime.utcnow()
        expiry = now + timedelta(hours=current_app.config['JWT_EXPIRY_HOURS'])
        token = generate_jwt({'administrator_id': administrator_id, 'refresh': False}, expiry)
        refresh_token = None
        if with_refresh_token:
            refresh_expiry = now + timedelta(days=current_app.config['JWT_REFRESH_DAYS'])
            refresh_token = generate_jwt({'administrator_id': administrator_id, 'refresh': True}, refresh_expiry)
        return token, refresh_token

    def get(self):
        """
        测试使用
        :return:
        """
        account = request.args.get('account')
        administrator = MisAdministrator.query.filter_by(account=account).first()
        if not administrator:
            return {'message': 'account not exits.'}, 400

        token, refresh_token = self._generate_tokens(administrator.id)
        data = dict(token=token,
                    refresh_token=refresh_token,
                    administrator_id=administrator.id,
                    group_id=administrator.group_id,
                    name=administrator.name)
        data['permission_tree'] = get_permission_tree(administrator.group_id)
        return data, 201

    def post(self):
        """
        登录创建token
        """
        req_parser = RequestParser()
        req_parser.add_argument('account', type=parser.mis_account, required=True, location='json')
        req_parser.add_argument('password', type=parser.mis_password, required=True, location='json')
        req_parser.add_argument('challenge', required=False, location='json')
        req_parser.add_argument('validate', required=False, location='json')
        req_parser.add_argument('seccode', required=False, location='json')

        args = req_parser.parse_args()

        if args.account != 'testid':
            if not all([args.challenge, args.validate, args.seccode]):
                return {'message': 'Missing params.'}, 400

            gt = GeetestLib(current_app.config['GEETEST_ID'], current_app.config['GEETEST_KEY'])
            # args.challenge = request.form[gt.FN_CHALLENGE]
            # args.validate = request.form[gt.FN_VALIDATE]
            # args.seccode = request.form[gt.FN_SECCODE]
            # args.account = 'wangzq01'
            # args.password = 'cz123456'

            status = session.get(gt.GT_STATUS_SESSION_KEY)
            if status:
                success = gt.success_validate(args.challenge, args.validate, args.seccode, args.account, data='', userinfo='')
            else:
                success = gt.failback_validate(args.challenge, args.validate, args.seccode)

            if not success:
                return {'message': 'Captcha validate failed.'}, 403

        administrator = MisAdministrator.query.filter_by(account=args.account).first()
        if administrator is None:
            return {'message': 'Please verify your real information in web.'}, 403

        if not check_password_hash(administrator.password, args.password):
            return {'message': 'Wrong password'}, 403

        token, refresh_token = self._generate_tokens(administrator.id)
        data = dict(token=token,
                    refresh_token=refresh_token,
                    administrator_id=administrator.id,
                    group_id=administrator.group_id,
                    name=administrator.name)
        data['permission_tree'] = get_permission_tree(administrator.group_id)

        administrator.last_login = datetime.now()
        return data, 201

    def put(self):
        """
        刷新token
        """
        administrator_id = g.administrator_id
        if administrator_id and g.refresh_token:
            token, refresh_token = self._generate_tokens(administrator_id, with_refresh_token=False)
            return {'token': token}, 201
        else:
            return {'message': 'Wrong refresh token.'}, 403


class PasswordResource(Resource):
    """
    密码
    """
    method_decorators = {
        'put': [mis_login_required],
    }

    def put(self):
        """
        修改密码
        :return:
        """
        json_parser = RequestParser()
        json_parser.add_argument('old_password', type=parser.mis_password, required=True, location='json')
        json_parser.add_argument('password', type=parser.mis_password, required=True, location='json')

        args = json_parser.parse_args()
        administrator = MisAdministrator.query.get(g.administrator_id)

        if not check_password_hash(administrator.password, args.old_password):
            return {'message': 'Old password wrong.'}, 403

        administrator.password = generate_password_hash(args.password)
        db.session.add(administrator)
        db.session.commit()
        return {'message': 'ok'}, 201

