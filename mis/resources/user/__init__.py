from flask import Blueprint
from flask_restful import Api

from utils.output import output_json
from . import user, legalize

user_bp = Blueprint('user', __name__)
user_api = Api(user_bp, catch_all_404s=True)
user_api.representation('application/json')(output_json)

# 用户列表
user_api.add_resource(user.UserListResource, '/v1_0/users',
                      endpoint='UserList')

# 单用户
user_api.add_resource(user.UserResource, '/v1_0/users/<int(min=1):target>',
                      endpoint='User')

# 用户认证申请记录
user_api.add_resource(legalize.LegalizeListResource, '/v1_0/legalizes',
                      endpoint='LegalizeList')

# 单用户认证申请记录
user_api.add_resource(legalize.LegalizeResource, '/v1_0/legalizes/<int(min=1):target>',
                      endpoint='Legalize')