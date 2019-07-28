from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from flask_restful import marshal, fields
from flask import current_app
import traceback


from utils.decorators import mis_login_required, mis_permission_required
from utils import parser
from cache.permission import inc_red_group_permission, get_permission_tree
from models.system import MisPermission, MisAdministrator, MisAdministratorGroup, MisGroupPermission
from models import db
from . import constants


class GroupListResource(Resource):
    """
    管理员角色/组管理
    """
    method_decorators = {
        'get': [mis_permission_required('group-list-get')],
        'post': [mis_permission_required('group-list-post')],
    }
    group_fields = {
        'group_id': fields.Integer(attribute='id'),
        'name': fields.String(attribute='name'),
        'remark': fields.String(attribute='remark'),
        'status': fields.Integer(attribute='status'),
    }

    def get(self):
        """
        获取所有组
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                 constants.PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args_parser.add_argument('keyword', location='args')
        args_parser.add_argument('order_by', location='args')
        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        groups = MisAdministratorGroup.query
        if args.keyword:
            groups = groups.filter(MisAdministratorGroup.name.like('%' + args.keyword + '%'))
        if args.order_by is not None:
            if args.order_by == 'id':
                groups = groups.order_by(MisAdministratorGroup.id.asc())
        else:
            groups = groups.order_by(MisAdministratorGroup.utime.desc())
        total_count = groups.count()
        groups = groups.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(groups, GroupListResource.group_fields, envelope='groups')
        ret['total_count'] = total_count
        return ret

    def post(self):
        """
        添加组
        """
        json_parser = RequestParser()
        json_parser.add_argument('name', required=True, location='json')
        json_parser.add_argument('remark', location='json')
        json_parser.add_argument('status', type=inputs.int_range(0, 1), location='json')
        json_parser.add_argument('permission_ids', action='append', type=inputs.positive,
                                 location='json')
        args = json_parser.parse_args()
        if MisAdministratorGroup.query.filter_by(name=args.name).first():
            return {'message': 'Group {} already exists.'.format(args.name)}, 403
        group = MisAdministratorGroup(name=args.name,
                                      remark=args.remark if args.remark else '',
                                      status=args.status if args.status is not None else 1)

        try:
            db.session.add(group)
            db.session.commit()
            print(args.permission_ids)
            if args.permission_ids:
                for index, permission_id in enumerate(args.permission_ids):
                    db.session.add(MisGroupPermission(group_id=group.id, permission_id=permission_id))
                    print(group.id, permission_id)
                    if (index + 1) % 1000 == 0:
                        db.session.commit()
                db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {'group_id': group.id, 'name': args.name}


class GroupResource(Resource):
    """
    对指定管理员组管理
    """
    method_decorators = {
        'get': [mis_permission_required('group-get')],
        'put': [mis_permission_required('group-put')],
        'delete': [mis_permission_required('group-delete')],
    }

    def get(self, target):
        """
        获取id=target组的信息
        """
        group = MisAdministratorGroup.query.filter_by(id=target).first()
        if not group:
            return {'message': 'Invalid group id.'}, 400
        ret = marshal(group, GroupListResource.group_fields)
        permission_tree = get_permission_tree(group.id)
        ret['permission_tree'] = permission_tree
        return ret

    def put(self, target):
        """
        修改id=target管理员组信息
        """
        json_parser = RequestParser()
        json_parser.add_argument('name', location='json')
        json_parser.add_argument('remark', location='json')
        json_parser.add_argument('status', type=inputs.int_range(0, 1), location='json')
        json_parser.add_argument('permission_ids', action='append', type=inputs.positive,
                                 location='json')
        args = json_parser.parse_args()
        print(args)
        group = MisAdministratorGroup.query.filter_by(id=target).first()
        if not group:
            return {'message': 'Invalid group id.'}, 400
        if args.name and args.name != group.name:
            if MisAdministratorGroup.query.filter_by(name=args.name).first():
                return {'message': '{} already exists'.format(args.name)}
            group.name = args.name
        if args.status is not None:
            group.status = args.status
        if args.remark:
            group.remark = args.remark
        if args.permission_ids is not None:
            inc_red_group_permission(group.id, args.permission_ids)
        db.session.add(group)
        db.session.commit()
        return marshal(group, GroupListResource.group_fields), 201

    def delete(self, target):
        """
        删除id=target管理员组信息
        """
        if MisAdministrator.query.filter_by(group_id=target).first():
            return {'message': 'Delete administrator first.'}, 400
        # 删除组权限信息
        MisGroupPermission.query.filter_by(group_id=target).delete(synchronize_session=False)
        # 删除组信息
        MisAdministratorGroup.query.filter_by(id=target).delete(synchronize_session=False)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

        return {'message': 'OK'}, 204
