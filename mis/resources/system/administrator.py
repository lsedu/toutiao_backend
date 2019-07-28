from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs, marshal, fields
from flask import g, request, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from werkzeug.security import generate_password_hash
import traceback


from utils.decorators import mis_permission_required
from models.system import *
from utils import parser
from models import db
from . import constants


class AdministratorListResource(Resource):
    """
    管理员管理
    """
    administrators_fields = {
        'administrator_id': fields.Integer(attribute='id'),
        'account': fields.String(attribute='account'),
        'email': fields.String(attribute='email'),
        'mobile': fields.String(attribute='mobile'),
        'name': fields.String(attribute='name'),
        'group_name': fields.String(attribute='group.name'),
        'group_id': fields.Integer(attribute='group_id'),
        'access_count': fields.Integer(attribute='access_count'),
        'status': fields.Integer(attribute='status'),
        'last_login': fields.Integer(attribute='last_login')
    }
    method_decorators = {
        'get': [mis_permission_required('administrator-list-get')],
        'post': [mis_permission_required('administrator-list-post')],
    }

    def post(self):
        """
        添加管理员
        """
        json_parser = RequestParser()
        json_parser.add_argument('account', type=parser.mis_account, required=True, location='json')
        json_parser.add_argument('password', type=parser.mis_password, required=True, location='json')
        json_parser.add_argument('group_id', type=parser.mis_group_id, required=True, location='json')
        json_parser.add_argument('name', required=True, location='json')
        args = json_parser.parse_args()
        administrator = MisAdministrator.query.filter_by(account=args.account).first()
        if administrator:
            return {'message': '{} already exists'.format(args.account)}, 403

        administrator = MisAdministrator(account=args.account,
                                         password=generate_password_hash(args.password),
                                         name=args.name,
                                         group_id=args.group_id)
        try:
            db.session.add(administrator)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {'account': args.account,
                'name': args.name}, 201

    def get(self):
        """
        管理员查询
        """
        args_parser = RequestParser()
        args_parser.add_argument('order_by', location='args')
        args_parser.add_argument('keyword', location='args')
        args_parser.add_argument('status', type=inputs.int_range(0, 1), location='args')
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                 constants.PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        administrators = MisAdministrator.query
        if args.status is not None:
            administrators = administrators.filter_by(status=args.status)
        if args.keyword:
            administrators = administrators.filter(or_(MisAdministrator.account.like('%' + args.keyword + '%'),
                                                       MisAdministrator.name.like('%' + args.keyword + '%')))
        if args.order_by is not None:
            if args.order_by == 'id':
                administrators = administrators.order_by(MisAdministrator.id.asc())
        else:
            administrators = administrators.order_by(MisAdministrator.utime.desc())
        total_count = administrators.count()
        administrators = administrators.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(administrators, AdministratorListResource.administrators_fields, envelope='administrators')
        ret['total_count'] = total_count
        return ret

    def delete(self):
        """
        批量删除管理员
        """
        json_parser = RequestParser()
        json_parser.add_argument('administrator_ids', action='append', type=inputs.positive, required=True, location='json')
        args = json_parser.parse_args()

        MisAdministrator.query.filter(MisAdministrator.id.in_(args.administrator_ids)).delete(synchronize_session=False)
        db.session.commit()
        return {'message': 'OK'}, 204


class AdministratorResource(Resource):
    """
    管理员管理
    """
    method_decorators = {
        'get': [mis_permission_required('administrator-get')],
        'put': [mis_permission_required('administrator-put')],
        'delete': [mis_permission_required('administrator-delete')],
    }

    def get(self, target):
        """
        获取管理员详情
        """
        administrator = MisAdministrator.query.filter_by(id=target).first()
        if not administrator:
            return {'message': 'Invalid administrator id.'}, 400
        return marshal(administrator, AdministratorListResource.administrators_fields)

    def put(self, target):
        """
        修改id=target管理员信息
        """
        json_parser = RequestParser()
        json_parser.add_argument('account', type=parser.mis_account, location='json')
        json_parser.add_argument('password', type=parser.mis_password, location='json')
        json_parser.add_argument('name', location='json')
        json_parser.add_argument('group_id', type=parser.mis_group_id, location='json')
        json_parser.add_argument('status', type=inputs.int_range(0, 1), location='json')

        json_parser.add_argument('email', type=parser.email, location='json')
        json_parser.add_argument('mobile', type=parser.mobile, location='json')
        json_parser.add_argument('current_password', type=parser.mis_password, location='json')

        args = json_parser.parse_args()
        print(args)
        administrator = MisAdministrator.query.filter_by(id=target).first()
        if not administrator:
            return {'message': 'Invalid administrator id.'}, 403

        if args.account and args.account != administrator.account:
            if MisAdministrator.query.filter_by(account=args.account).first():
                return {'message': '{} already exists'.format(args.account)}
            administrator.account = args.account
        if args.password:
            if target == g.administrator_id \
                    and administrator.password != generate_password_hash(args.current_password):
                return {'message': 'Current password error.'}, 403

            administrator.password = generate_password_hash(args.password)
        if args.name:
            administrator.name = args.name
        if args.group_id:
            administrator.group_id = args.group_id
        if args.status is not None:
            administrator.status = args.status
        if args.email:
            administrator.email = args.email
        if args.mobile:
            administrator.mobile = args.mobile

        try:
            db.session.add(administrator)
            db.session.commit()
        except:
            db.session.rollback()
            raise

        return marshal(administrator, AdministratorListResource.administrators_fields), 201

    def delete(self, target):
        """
        删除id=target管理员信息
        """
        MisAdministrator.query.filter_by(id=target).delete(synchronize_session=False)
        db.session.commit()
        return {'message': 'OK'}, 204


class AdministratorInitResource(Resource):
    """
    初始化
    """
    def _get_init_permissions(self):
        permissions = [
            # 菜单
            {
                'id': 1,
                'name': '首页',
                'code': '/home',
                'type': 0,
                'sequence': 1,
            },
            {
                'id': 2,
                'name': '用户管理',
                'type': 0,
                'sequence': 2,
            },
            {
                'id': 3,
                'name': '信息管理',
                'type': 0,
                'sequence': 3,
            },
            {
                'id': 4,
                'name': '数据统计',
                'type': 0,
                'sequence': 4,
            },
            {
                'id': 5,
                'name': '系统管理',
                'type': 0,
                'sequence': 5,
            },
            {
                'id': 6,
                'name': '推荐系统',
                'type': 0,
                'sequence': 6,
            },
            # 二级菜单
            {
                'id': 7,
                'name': '用户列表',
                'code': '/home/user',
                'type': 0,
                'sequence': 1,
                'parent_id': 2
            },
            {
                'id': 8,
                'name': '用户审核',
                'code': '/home/userAudit',
                'type': 0,
                'sequence': 2,
                'parent_id': 2
            },
            {
                'id': 9,
                'name': '频道管理',
                'code': '/home/channels',
                'type': 0,
                'sequence': 1,
                'parent_id': 3
            },
            {
                'id': 10,
                'name': '内容管理',
                'code': '/home/contents',
                'type': 0,
                'sequence': 2,
                'parent_id': 3
            },
            {
                'id': 11,
                'name': '内容审核',
                'code': '/home/contentAudit',
                'type': 0,
                'sequence': 3,
                'parent_id': 3
            },
            {
                'id': 12,
                'name': '网站统计',
                'code': '/home/websiteStatistics',
                'type': 0,
                'sequence': 1,
                'parent_id': 4
            },
            {
                'id': 13,
                'name': '内容统计',
                'code': '/home/contentStatistics',
                'type': 0,
                'sequence': 2,
                'parent_id': 4
            },
            {
                'id': 14,
                'name': '管理员管理',
                'code': '/home/admins',
                'type': 0,
                'sequence': 1,
                'parent_id': 5
            },
            {
                'id': 15,
                'name': '角色管理',
                'code': '/home/role',
                'type': 0,
                'sequence': 2,
                'parent_id': 5

            },
            {
                'id': 16,
                'name': '权限管理',
                'code': '/home/power',
                'type': 0,
                'sequence': 3,
                'parent_id': 5

            },
            {
                'id': 17,
                'name': '运营日志',
                'code': '/home/operationLog',
                'type': 0,
                'sequence': 4,
                'parent_id': 5

            },
            {
                'id': 18,
                'name': '个人信息',
                'code': '/home/perInfo',
                'type': 0,
                'sequence': 5,
                'parent_id': 5

            },

            {
                'id': 19,
                'name': '修改密码',
                'code': '/home/reSetPWD',
                'type': 0,
                'sequence': 6,
                'parent_id': 5

            },
            {
                'id': 20,
                'name': '敏感词设置',
                'code': '/home/sensitiveSet',
                'type': 0,
                'sequence': 1,
                'parent_id': 6
            },
            # 权限点
            {
                "name": "用户列表查询",
                "code": "userlist-get",
                'parent_id': 7,
            },
            {
                "name": "用户新增",
                "code": "userlist-post",
                'parent_id': 7,
            },
            {
                'name': '用户编辑',
                'code': 'userlist-put',
                'parent_id': 7,
            },
            {
                "name": "用户详情查询",
                "code": "user-get",
                'parent_id': 7,
            },
            {
                "name": "用户认证记录查询",
                "code": "legalize-list-get",
                'parent_id': 8,
            },
            {
                "name": "用户认证审核",
                "code": "legalize-list-put",
                'parent_id': 8,
            },
            {
                "name": "用户认证记录详细查询",
                "code": "legalize-get",
                'parent_id': 8
            },
            {
                "name": "MIS用户列表查询",
                "code": "administrator-list-get",
                'parent_id': 14
            },
            {
                "name": "MIS用户删除",
                "code": "administrator-delete",
                'parent_id': 14
            },
            {
                "name": "MIS用户批量编辑",
                "code": "administrator-list-post",
                'parent_id': 14
            },
            {
                "name": "MIS用户详情查询",
                "code": "administrator-get",
                'parent_id': 14
            },
            {
                "name": "MIS用户编辑",
                "code": "administrator-put",
                'parent_id': 14
            },

            {
                "name": "角色列表查询",
                "code": "group-list-get",
                'parent_id': 15
            },
            {
                "name": "角色编辑",
                "code": "group-put",
                'parent_id': 15,
            },
            {
                "name": "角色新建",
                "code": "group-list-post",
                'parent_id': 15
            },
            {
                "name": "角色删除",
                "code": "group-delete",
                'parent_id': 15
            },
            {
                "name": "角色详情查询",
                "code": "group-get",
                'parent_id': 15
            },
            {
                "name": "运营日志查询",
                "code": "operationlog-get",
                'parent_id': 17
            },

            {
                "name": "权限列表查询",
                "code": "permission-list-get",
                'parent_id': 16
            },

            {
                "name": "权限详情查询",
                "code": "permission-get",
                'parent_id': 16
            },

            {
                "name": "权限新建",
                "code": "permission-list-post",
                'parent_id': 16
            },
            {
                "name": "权限删除",
                "code": "permission-delete",
                'parent_id': 16
            },
            {
                "name": "权限修改",
                "code": "permission-put",
                'parent_id': 16
            },

            {
                "name": "敏感词列表查询",
                "code": "sensitive-word-list-get",
                'parent_id': 20
            },
            {
                "name": "敏感词新建",
                "code": "sensitive-word-list-post",
                'parent_id': 20
            },
            {
                "name": "敏感词查询",
                "code": "sensitive-word-get",
                'parent_id': 20
            },
            {
                "name": "敏感词修改",
                "code": "sensitive-word-put",
                'parent_id': 20
            },
            {
                "name": "敏感词删除",
                "code": "sensitive-word-delete",
                'parent_id': 20
            },
            {
                "name": "基本统计查询",
                "code": "statistics-basic-get",
                'parent_id': 12
            },
            {
                "name": "搜索统计查询",
                "code": "statistics-search-get",
                'parent_id': 12
            },
            {
                "name": "搜索统计总数查询",
                "code": "statistics-search-total-get",
                'parent_id': 12
            },
            {
                "name": "销售额统计查询",
                "code": "statistics-sales-total-get",
                'parent_id': 12
            },
            {
                "name": "阅读来源统计查询",
                "code": "statistics-read-source-total-get",
                'parent_id': 12
            },
            {
                "name": "文章列表查询",
                "code": "article-list-get",
                'parent_id': 10
            },
            {
                "name": "文章设置",
                "code": "article-list-put",
                'parent_id': 11
            },
            {
                "name": "文章详情查询",
                "code": "article-get",
                'parent_id': 10
            },

            {
                "name": "频道列表查询",
                "code": "channel-list-get",
                'parent_id': 9
            },
            {
                "name": "频道新建",
                "code": "channel-list-post",
                'parent_id': 9
            },
            {
                "name": "频道修改",
                "code": "channel-list-put",
                'parent_id': 9
            },
            {
                "name": "频道删除",
                "code": "channel-list-delete",
                'parent_id': 9
            },
        ]
        return permissions

    def _get_permission_ids(self):
        permissions = self._get_init_permissions()
        permissions_ids = []
        for p in permissions:
            obj = MisPermission.query.filter_by(name=p['name']).first()
            if not obj:
                # obj = MisPermission(name=p['name'], code=p['code'], type=p.get('type', 1))
                obj = MisPermission(**p)
                db.session.add(obj)
                db.session.commit()
            permissions_ids.append(obj.id)
        return permissions_ids

    def _get_group_id(self):
        name = '超级管理员'
        group = MisAdministratorGroup.query.filter_by(name=name).first()
        if not group:
            group = MisAdministratorGroup(name=name)
            db.session.add(group)
            db.session.commit()
        permissions_ids = self._get_permission_ids()
        for pid in permissions_ids:
            gp = MisGroupPermission.query.filter_by(group_id=group.id, permission_id=pid).first()
            if not gp:
                gp = MisGroupPermission(group_id=group.id, permission_id=pid)
                db.session.add(gp)
                db.session.commit()
        return group.id

    def _create_init_administrator(self):
        account = 'admin'
        password = 'cs_itcast'
        name = '初始化管理员'
        group_id = self._get_group_id()
        admin = MisAdministrator.query.filter_by(account=account).first()
        if not admin:
            admin = MisAdministrator(account=account,
                                     password=generate_password_hash(password),
                                     group_id=group_id,
                                     name=name)
            db.session.add(admin)
            db.session.commit()

    def _mis_init(self):
        key = 'mis_init'
        cli = current_app.redis_cli['comm_cache']
        if not cli.get(key):
            cli.setex(key, 60, 1)
            print(key)
            self._create_init_administrator()

    def get(self):
        """
        创建初始权限、组、管理员
        :return:
        """
        # mis系统初始化
        if current_app.config.get('IS_INIT'):
            self._mis_init()
        return {'message': 'ok'}

