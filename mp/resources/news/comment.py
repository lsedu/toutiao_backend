from flask_restful import Resource
from flask import g, current_app
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from redis.exceptions import RedisError

from utils.decorators import verify_required
from models.news import Article, Comment, CommentLiking
from models import db
from . import constants
from cache import comment as cache_comment
from cache import article as cache_article
from cache import statistic as cache_statistic
from utils import parser


class CommentStatusResource(Resource):
    """
    评论状态
    """
    method_decorators = [verify_required]

    def put(self):
        """
        修改评论状态
        """
        req_parser = RequestParser()
        req_parser.add_argument('article_id', type=inputs.positive, required=True, location='args')
        req_parser.add_argument('allow_comment', type=inputs.boolean, required=True, location='json')
        args = req_parser.parse_args()

        ret = Article.query.filter_by(id=args.article_id, user_id=g.user_id, status=Article.STATUS.APPROVED)\
            .update({'allow_comment': args.allow_comment})
        db.session.commit()

        if ret > 0:
            cache_article.ArticleInfoCache(args.article_id).clear()
            return {'article_id': args.article_id, 'allow_comment': args.allow_comment}, 201
        else:
            return {'message': 'Invalid article status.'}, 400


class CommentListResource(Resource):
    """
    评论
    """
    method_decorators = [verify_required]

    def _comment_type(self, value):
        """
        检查评论类型参数
        """
        if value in ('a', 'c'):
            return value
        else:
            raise ValueError('Invalid type param.')

    def get(self):
        """
        获取评论
        """
        # /comments?type,source,offset,limit
        # return = {
        #     'results': [
        #         {
        #             'com_id': 0,
        #             'aut_id': 0,
        #             'aut_name': '',
        #             'aut_photo': '',
        #             'like_count': 0,
        #             'reply_count': 0,
        #             'pubdate': '',
        #             'content': ''
        #         }
        #     ],
        #     'total_count': 0,
        #     'last_id': 0,
        #     'end_id': 0,
        # }
        qs_parser = RequestParser()
        qs_parser.add_argument('type', type=self._comment_type, required=True, location='args')
        qs_parser.add_argument('source', type=inputs.positive, required=True, location='args')
        qs_parser.add_argument('offset', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('limit', type=inputs.int_range(constants.DEFAULT_COMMENT_PER_PAGE_MIN,
                                                              constants.DEFAULT_COMMENT_PER_PAGE_MAX,
                                                              argument='limit'), required=False, location='args')
        args = qs_parser.parse_args()
        limit = args.limit if args.limit is not None else constants.DEFAULT_COMMENT_PER_PAGE_MIN

        result = {}

        if args.type == 'a':
            # 文章评论
            article_id = args.source
            article_info_cache = cache_article.ArticleInfoCache(article_id)
            if not article_info_cache.exists():
                return {'Article not exists.'}, 400
            total_count, end_id, last_id, ret = cache_comment.ArticleCommentsCache(article_id)\
                .get_page(args.offset, limit)
            article = article_info_cache.get()
            result['art_id'] = article_id
            result['art_title'] = article['title']
            result['art_pubdate'] = article['pubdate']
        else:
            # 评论的评论
            comment_id = args.source
            if not cache_comment.CommentCache(comment_id).exists():
                return {'Comment not exists.'}, 400
            total_count, end_id, last_id, ret = cache_comment.CommentRepliesCache(comment_id).get_page(args.offset,
                                                                                                       limit)
        results = cache_comment.CommentCache.get_list(ret)

        # 判断当前用户是否有点赞行为
        liking_comments = []
        if ret:
            liking_ret = CommentLiking.query.options(load_only(CommentLiking.comment_id))\
                .filter(CommentLiking.comment_id.in_(ret), CommentLiking.user_id == g.user_id,
                        CommentLiking.is_deleted == 0).all()
            liking_comments = [comment_liking.comment_id for comment_liking in liking_ret]
        liking_comments = set(liking_comments)
        for comment in results:
            comment['is_liking'] = 1 if comment['com_id'] in liking_comments else 0

        result.update({'total_count': total_count, 'end_id': end_id, 'last_id': last_id, 'results': results})
        return result

    def post(self):
        """
        创建评论
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=inputs.positive, required=True, location='json')
        json_parser.add_argument('content', required=True, location='json')
        json_parser.add_argument('art_id', type=parser.article_id, required=True, location='json')

        args = json_parser.parse_args()
        target = args.target
        content = args.content
        article_id = args.art_id

        if not content:
            return {'message': 'Empty content.'}, 400

        allow_comment = cache_article.ArticleInfoCache(article_id).determine_allow_comment()
        if not allow_comment:
            return {'message': 'Article denied comment.'}, 403

        # 对评论的回复
        ret = Comment.query.options(load_only(Comment.id)).filter_by(id=target, article_id=article_id).first()
        if ret is None:
            return {'message': 'Invalid target comment id.'}, 400

        comment_id = current_app.id_worker.get_id()
        comment = Comment(id=comment_id, user_id=g.user_id, article_id=article_id, parent_id=target, content=content)
        db.session.add(comment)
        db.session.commit()

        # TODO 增加评论审核后 在评论审核中添加缓存
        cache_statistic.ArticleCommentCountStorage.incr(article_id)
        cache_statistic.CommentReplyCountStorage.incr(target)
        try:
            cache_comment.CommentCache(comment_id).save(comment)
        except SQLAlchemyError as e:
            current_app.logger.error(e)
        cache_comment.CommentRepliesCache(target).add(comment)

        return {'com_id': comment.id, 'target': target, 'art_id': article_id}, 201


class CommentResource(Resource):
    """
    评论
    """
    method_decorators = [verify_required]

    def delete(self, target):
        """
        删除评论
        """
        comment = Comment.query.options(load_only(Comment.user_id, Comment.article_id, Comment.parent_id), joinedload(Comment.article, innerjoin=True)
                                        .load_only(Article.user_id)).filter_by(id=target).first()

        if comment.article.user_id != g.user_id:
            return {'message': 'User has no permission to delete this comment.'}, 403

        Comment.query.filter_by(id=target).update({'status': Comment.STATUS.DELETED})
        db.session.commit()

        try:
            if comment.parent_id is not None:
                cache_comment.CommentRepliesCache(comment.parent_id).clear()
                cache_statistic.CommentReplyCountStorage.incr(comment.parent_id, -1)
            else:
                cache_comment.ArticleCommentsCache(comment.article_id).clear()
            cache_statistic.ArticleCommentCountStorage.incr(comment.article_id, -1)
        except RedisError as e:
            current_app.logger.error(e)

        return {'message': 'OK'}, 204


class CommentStickyResource(Resource):
    """
    评论置顶
    """
    method_decorators = [verify_required]

    def put(self, target):
        """
        评论置顶
        """
        req_parser = RequestParser()
        req_parser.add_argument('sticky', type=inputs.boolean, required=True, location='json')
        args = req_parser.parse_args()

        comment = Comment.query.options(load_only(Comment.user_id), joinedload(Comment.article, innerjoin=True)
                                        .load_only(Article.user_id)).filter_by(id=target).first()

        if comment.article.user_id != g.user_id:
            return {'message': 'User has no permission to delete this comment.'}, 403

        Comment.query.filter_by(id=target).update({'is_top': args.sticky})
        db.session.commit()
        try:
            cache_comment.CommentCache(target).clear()
        except RedisError as e:
            current_app.logger.error(e)

        return {'target': target, 'sticky': args.sticky}


class CommentLikingListResource(Resource):
    """
    评论点赞
    """
    method_decorators = [verify_required]

    def post(self):
        """
        评论点赞
        """
        json_parser = RequestParser()
        json_parser.add_argument('target', type=parser.comment_id, required=True, location='json')
        args = json_parser.parse_args()
        target = args.target
        ret = 1
        try:
            comment_liking = CommentLiking(user_id=g.user_id, comment_id=target)
            db.session.add(comment_liking)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            ret = CommentLiking.query.filter_by(user_id=g.user_id, comment_id=target, is_deleted=True) \
                .update({'is_deleted': False})
            db.session.commit()

        if ret > 0:
            cache_statistic.CommentLikingCountStorage.incr(target)
        return {'target': target}, 201


class CommentLikingResource(Resource):
    """
    评论点赞
    """
    method_decorators = [verify_required]

    def delete(self, target):
        """
        取消对评论点赞
        """
        ret = CommentLiking.query.filter_by(user_id=g.user_id, comment_id=target, is_deleted=False) \
            .update({'is_deleted': True})
        db.session.commit()

        if ret > 0:
            cache_statistic.CommentLikingCountStorage.incr(target, -1)
        return {'message': 'OK'}, 204


