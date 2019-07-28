from flask import Blueprint
from flask_restful import Api

from utils.output import output_json
from . import channel, article

information_bp = Blueprint('information', __name__)
information_api = Api(information_bp, catch_all_404s=True)
information_api.representation('application/json')(output_json)

# 频道列表
information_api.add_resource(channel.ChannelListResource, '/v1_0/channels',
                      endpoint='ChannelList')

# 频道
information_api.add_resource(channel.ChannelResource, '/v1_0/channels/<int(min=1):target>',
                      endpoint='Channel')

# 文章列表
information_api.add_resource(article.ArticleListResource, '/v1_0/articles',
                      endpoint='ArticleList')

# 文章
information_api.add_resource(article.ArticleResource, '/v1_0/articles/<int(min=1):target>',
                      endpoint='Article')

