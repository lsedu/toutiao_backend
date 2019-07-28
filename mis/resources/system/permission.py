from flask_restful import Resource, inputs, fields, marshal
from flask_restful.reqparse import RequestParser
from flask import g, request, current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.orm import load_only
import traceback

from utils.decorators import mis_permission_required
from models.system import MisPermission, MisGroupPermission
from utils import parser
from . import constants
from models import db
from cache.permission import get_children_permission_ids


class PermissionListResource(Resource):
    """
    权限管理
    """
    method_decorators = {
        'get': [mis_permission_required('permission-list-get')],
        'post': [mis_permission_required('permission-list-post')],
    }
    permission_fields = {
        'permission_id': fields.Integer(attribute='id'),
        'name': fields.String(attribute='name'),
        'type': fields.Integer(attribute='type'),
        'parent_id': fields.Integer(attribute='parent_id'),
        'code': fields.String(attribute='code'),
        'sequence': fields.Integer(attribute='sequence'),
    }

    def get(self):
        """
        获取权限列表
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('keyword', location='args')
        args_parser.add_argument('order_by', location='args')
        args_parser.add_argument('parent_id', type=parser.mis_permission_id, required=False, location='args')
        args_parser.add_argument('type', type=inputs.int_range(0, 1), location='args')
        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        permissions = MisPermission.query
        if args.parent_id >= 0:
            permissions = permissions.filter_by(parent_id=args.parent_id)
        if args.type is not None:
            permissions = permissions.filter_by(type=args.type)
        if args.keyword:
            permissions = permissions.filter(or_(MisPermission.name.like('%' + args.keyword + '%'),
                                                 MisPermission.code.like('%' + args.keyword + '%')))
        if args.order_by is not None:
            if args.order_by == 'id':
                permissions = permissions.order_by(MisPermission.id.asc())
            else:
                permissions = permissions.order_by(MisPermission.sequence.asc())
        else:
            permissions = permissions.order_by(MisPermission.sequence.asc())
        total_count = permissions.count()
        permissions = permissions.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(permissions, PermissionListResource.permission_fields, envelope='permissions')
        ret['total_count'] = total_count
        return ret

    def post(self):
        """
        新建权限
        """
        json_parser = RequestParser()
        json_parser.add_argument('name', required=True, location='json')
        json_parser.add_argument('type', type=inputs.int_range(0,1), required=True, location='json')
        json_parser.add_argument('parent_id', type=inputs.natural, location='json')
        json_parser.add_argument('code', required=True, location='json')
        json_parser.add_argument('sequence', required=inputs.natural, location='json')
        args = json_parser.parse_args()
        if MisPermission.query.filter_by(name=args.name).first():
            return {'message': '{} already exists'.format(args.name)}

        parent_id = args.parent_id if args.parent_id else 0
        if parent_id and not MisPermission.query.filter_by(id=parent_id, type=MisPermission.TYPE.MENU).first():
            return {'message': 'Parent({}) permission does not exist'.format(args.parent_id)}

        permission = MisPermission(name=args.name,
                                   type=args.type,
                                   parent_id=parent_id,
                                   code=args.code,
                                   sequence=args.sequence)
        db.session.add(permission)
        db.session.commit()
        return marshal(permission, PermissionListResource.permission_fields), 201


class PermissionResource(Resource):
    """
    权限管理
    """
    method_decorators = {
        'get': [mis_permission_required('permission-get')],
        'put': [mis_permission_required('permission-put')],
        'delete': [mis_permission_required('permission-delete')],
    }

    def _get_permission(self, target):
        return MisPermission.query.filter_by(id=target).first()

    def get(self, target):
        """
        获取权限详情
        """
        permission = MisPermission.query.filter_by(id=target).first()
        if not permission:
            return {'message': 'Invalid permission id.'}, 400
        return marshal(permission, PermissionListResource.permission_fields)

    def put(self, target):
        """
        修改id=target权限详情
        """
        json_parser = RequestParser()
        json_parser.add_argument('name', location='json')
        json_parser.add_argument('type', type=inputs.int_range(0,1), location='json')
        json_parser.add_argument('parent_id', type=inputs.natural, location='json')
        json_parser.add_argument('code', location='json')
        json_parser.add_argument('sequence', type=inputs.positive, location='json')
        args = json_parser.parse_args()
        permission = self._get_permission(target)
        if not permission:
            return {'message': 'Invalid permission id.'}, 400
        if args.name and args.name != permission.name:
            if MisPermission.query.filter_by(name=args.name).first():
                return {'message': '{} already exists'.format(args.name)}
            permission.name = args.name
        if args.type is not None:
            permission.type = args.type
        if args.parent_id and args.parent_id != permission.parent_id:
            if not MisPermission.query.filter_by(id=args.parent_id).first():
                return {'message': 'Parent({}) permission does not exist'.format(args.parent_id)}
            permission.parent_id = args.parent_id
        if args.code:
            permission.code = args.code
        if args.sequence:
            permission.sequence = args.sequence

        db.session.add(permission)
        db.session.commit()

        return marshal(permission, PermissionListResource.permission_fields), 201

    def delete(self, target):
        """
        删除id=target权限详情
        """
        args_parser = RequestParser()
        args_parser.add_argument('del_children', type=inputs.positive, location='args')
        args = args_parser.parse_args()
        print('args:', args)
        if  args.del_children is None \
            and MisPermission.query.filter_by(parent_id=target).first():
            return {'message': 'There are subdirectories that cannot be deleted.'}, 400

        # 获取target和子权限id
        del_permission_ids = [target] + get_children_permission_ids(target)

        # 删除跟target和它的子权限相关的组权限
        MisGroupPermission.query.filter(MisGroupPermission.permission_id.in_(del_permission_ids))\
            .delete(synchronize_session=False)

        # 删除target和它的子权限
        MisPermission.query.filter(MisPermission.id.in_(del_permission_ids)).delete(synchronize_session=False)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {'message': 'OK'}, 204

