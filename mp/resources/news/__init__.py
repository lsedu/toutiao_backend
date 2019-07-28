from flask import Blueprint
from flask_restful import Api

from . import material, channel, article, search, comment
from utils.output import output_json

news_bp = Blueprint('news', __name__)
news_api = Api(news_bp, catch_all_404s=True)
news_api.representation('application/json')(output_json)


news_api.add_resource(material.ImageListResource, '/v1_0/user/images',
                      endpoint='UserImages')

news_api.add_resource(material.ImageResource, '/v1_0/user/images/<int(min=1):target>',
                      endpoint='UserImage')

news_api.add_resource(channel.ChannelListResource, '/v1_0/channels',
                      endpoint='Channels')

news_api.add_resource(article.ArticleListResource, '/v1_0/articles',
                      endpoint='Articles')

news_api.add_resource(article.ArticleResource, '/v1_0/articles/<int(min=1):target>',
                      endpoint='Article')

news_api.add_resource(search.SearchResource, '/v1_0/search',
                      endpoint='Search')

news_api.add_resource(comment.CommentStatusResource, '/v1_0/comments/status',
                      endpoint='CommentsStatus')

news_api.add_resource(comment.CommentListResource, '/v1_0/comments',
                      endpoint='Comments')

news_api.add_resource(comment.CommentResource, '/v1_0/comments/<int(min=1):target>',
                      endpoint='Comment')

news_api.add_resource(comment.CommentStickyResource, '/v1_0/comments/<int(min=1):target>/sticky',
                      endpoint='StickComment')

news_api.add_resource(comment.CommentLikingListResource, '/v1_0/comment/likings',
                      endpoint='CommentLikings')

news_api.add_resource(comment.CommentLikingResource, '/v1_0/comment/likings/<int(min=1):target>',
                      endpoint='CommentLiking')
