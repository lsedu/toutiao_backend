from flask import Blueprint
from flask_restful import Api

from utils.output import output_json
from . import sensitive

recommend_bp = Blueprint('recommend', __name__)
recommend_api = Api(recommend_bp, catch_all_404s=True)
recommend_api.representation('application/json')(output_json)


# 敏感词
recommend_api.add_resource(sensitive.SensitiveWordListResource, '/v1_0/sensitive_words',
                      endpoint='SensitiveWordList')

# 单敏感词
recommend_api.add_resource(sensitive.SensitiveWordResource, '/v1_0/sensitive_words/<int(min=1):target>',
                      endpoint='SensitiveWord')