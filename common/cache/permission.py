from models.system import MisPermission, MisGroupPermission
from sqlalchemy.orm import load_only
from flask import current_app
from models import db
import traceback


def _permission_to_dict(permission):
    if isinstance(permission, dict):
        return {
            "permission_id": permission['id'],
            "name": permission['name'],
            "type": permission['type'],
            "parent_id": permission['parent_id'],
            "code": permission['code'],
            "sequence": permission['sequence']
        }
    else:
        return {
            "permission_id": permission.id,
            "name": permission.name,
            "type": permission.type,
            "parent_id": permission.parent_id,
            "code": permission.code,
            "sequence": permission.sequence
        }


def _get_permission_children(parent_id, permissions, group_permission_ids):
    # 递归，按照sequence排序获取子权限
    _permissions = [i for i in permissions if i['parent_id'] == parent_id]
    sorted(_permissions, key=lambda x:x['sequence'], reverse=False)
    if _permissions:
        children=[]
        for permission in _permissions:
            data = permission
            data['checked'] = 1 if permission['permission_id'] in group_permission_ids else 0
            data['children'] = _get_permission_children(permission['permission_id'],
                                                        permissions, group_permission_ids)
            children.append(data)
        return children
    return []


def permission_list_to_tree(permissions, group_permission_ids):
    # 把列表形式的权限改成树状
    tree = _get_permission_children(0, permissions, group_permission_ids)
    return tree


def permission_tree_to_list(permissions):
    # 递归，把树状转换成列表
    lst = []
    for i in permissions:
        lst.append(_permission_to_dict(i))
        if i['children']:
            lst = lst + permission_tree_to_list(i['children'])
    return lst


def get_children_permission_ids(parent_id):
    # 获取子权限id列表
    lst = []
    permissions = MisPermission.query.filter_by(parent_id=parent_id).all()
    if permissions:
        for i in permissions:
            lst.append(i.id)
            lst = lst + get_children_permission_ids(i.id)
    return lst


def get_group_permission_ids(group_id):
    # 获取组id=group_id的所有权限id
    permissions = MisGroupPermission.query.options(load_only(MisGroupPermission.permission_id))\
        .filter_by(group_id=group_id).all()
    return [i.permission_id for i in permissions]


def get_permissions():
    permissions = MisPermission.query.all()
    return [_permission_to_dict(permission) for permission in permissions]


def get_permission_tree(group_id):
    group_permission_ids = get_group_permission_ids(group_id)
    print(group_permission_ids)
    permissions = get_permissions()
    tree = _get_permission_children(0, permissions, group_permission_ids)
    return tree


def reset_group_permission(group_id, permission_ids):
    # 重置组权限
    try:
        MisGroupPermission.query.filter_by(group_id=group_id).delete(synchronize_session=False)
        for index, permission_id in enumerate(permission_ids):
            db.session.add(MisGroupPermission(group_id=group_id, permission_id=permission_id))
            if (index + 1) % 1000 == 0:
                db.session.commit()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise traceback.format_exc()


def inc_red_group_permission(group_id, permission_ids):
    # 增量添加组权限, 减量删除组权限
    try:
        group_permissions = MisGroupPermission.query.options(load_only(MisGroupPermission.permission_id))\
            .filter_by(group_id=group_id).all()
        existing_ids = [i.permission_id for i in group_permissions]
        increment_ids = set(permission_ids) - set(existing_ids)
        reduction_ids = set(existing_ids) - set(permission_ids)

        # 添加增量权限
        for index, permission_id in enumerate(increment_ids):
            db.session.add(MisGroupPermission(group_id=group_id, permission_id=permission_id))
            if (index + 1) % 1000 == 0:
                db.session.commit()

        # 删除减量权限
        MisGroupPermission.query.filter_by(group_id=group_id)\
            .filter(MisGroupPermission.permission_id.in_(reduction_ids)).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.error(traceback.format_exc())
        raise ValueError('db error')
