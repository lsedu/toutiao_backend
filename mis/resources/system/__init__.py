from flask import Blueprint
from flask_restful import Api

from utils.output import output_json
from . import passport, administrator, group, permission, operationlog


system_bp = Blueprint('system', __name__)
system_api = Api(system_bp, catch_all_404s=True)
system_api.representation('application/json')(output_json)

# 极验--验证码
system_api.add_resource(passport.CaptchaResource, '/v1_0/captchas/<string:account>',
                      endpoint='Captcha')

# 登录认证
system_api.add_resource(passport.AuthorizationResource, '/v1_0/authorizations',
                      endpoint='Authorization')

# 密码
system_api.add_resource(passport.PasswordResource, '/v1_0/password',
                      endpoint='Password')

# 管理员(增加，查询，批量删除)
system_api.add_resource(administrator.AdministratorListResource, '/v1_0/administrators',
                      endpoint='AdministratorList')

# 单个管理员(详情，修改，删除)
system_api.add_resource(administrator.AdministratorResource, '/v1_0/administrators/<int(min=1):target>',
                      endpoint='Administrator')

# 管理员角色/组(增加，查询)
system_api.add_resource(group.GroupListResource, '/v1_0/groups',
                      endpoint='GroupList')

# 单个管理员角色/组(详情，)
system_api.add_resource(group.GroupResource, '/v1_0/groups/<int(min=1):target>',
                      endpoint='Group')

# 权限（增加，查询）
system_api.add_resource(permission.PermissionListResource, '/v1_0/permissions',
                      endpoint='PermissionList')

# 单个权限（增加，查询）
system_api.add_resource(permission.PermissionResource, '/v1_0/permissions/<int(min=1):target>',
                      endpoint='Permission')

# 运营日志
system_api.add_resource(operationlog.OperationLogListResource, '/v1_0/operationlogs',
                      endpoint='OperationLogList')

# 初始化mis系统
system_api.add_resource(administrator.AdministratorInitResource, '/v1_0/administrators/init',
                        endpoint='AdministratorInit')
