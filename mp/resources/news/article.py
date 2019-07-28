from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from flask import current_app, g
import re
import random
from sqlalchemy import func
from sqlalchemy.orm import load_only, contains_eager
from datetime import timedelta

from utils.decorators import verify_required
from utils import parser
from models.news import Article, ArticleContent, ArticleStatistic
from models import db
from . import constants
from cache import user as cache_user
from cache import article as cache_article
from cache import statistic as cache_statistic


class ArticleResourceBase(Resource):
    """
    文章基类
    """
    def _cover(self, value):
        error_msg = 'Invalid cover param.'
        if not isinstance(value, dict):
            raise ValueError(error_msg)

        cover_type = value.get('type')
        if cover_type not in (-1, 0, 1, 3):
            raise ValueError(error_msg)

        images = value.get('images')
        if not isinstance(images, list) or (cover_type != -1 and len(images) != cover_type):
            raise ValueError(error_msg)

        for image in images:
            if not image.startswith(current_app.config['QINIU_DOMAIN']):
                raise ValueError(error_msg)

        return value

    def _generate_article_cover(self, content):
        """
        生成文章封面
        :param content: 文章内容
        """
        results = re.findall(r'src=\"(' + current_app.config['QINIU_DOMAIN'] + r'[^"]+)\"', content)
        length = len(results)
        if length <= 0:
            return {'type': 0, 'images': []}
        elif length < 3:
            img_url = random.choice(results)
            return {'type': 1, 'images': [img_url]}
        else:
            random.shuffle(results)
            img_urls = results[:3]
            return {'type': 3, 'images': img_urls}

    def _channel_id(self, value):
        value = parser.channel_id(value)
        if value == 0:
            raise ValueError('Invalid channel id param.')
        return value


class ArticleListResource(ArticleResourceBase):
    """
    文章
    """
    method_decorators = [verify_required]

    def post(self):
        """
        发表文章
        """
        req_parser = RequestParser()
        req_parser.add_argument('draft', type=inputs.boolean, required=False, location='args')
        req_parser.add_argument('title', type=inputs.regex(r'.{5,30}'), required=True, location='json')
        req_parser.add_argument('content', type=inputs.regex(r'.+'), required=True, location='json')
        req_parser.add_argument('cover', type=self._cover, required=True, location='json')
        req_parser.add_argument('channel_id', type=self._channel_id, required=True, location='json')
        args = req_parser.parse_args()
        content = args['content']
        cover = args['cover']
        draft = args['draft']

        # 对于自动封面，生成封面
        cover_type = cover['type']
        if cover_type == -1:
            cover = self._generate_article_cover(content)

        article_id = current_app.id_worker.get_id()

        # TODO 暂时增加特权帐号，文章直接为审核通过状态
        if draft:
            article_status = Article.STATUS.DRAFT
        else:
            article_status = Article.STATUS.APPROVED if g.user_id == 1 else Article.STATUS.UNREVIEWED

        article = Article(
            id=article_id,
            user_id=g.user_id,
            channel_id=args['channel_id'],
            title=args['title'],
            cover=cover,
            # status=Article.STATUS.DRAFT if draft else Article.STATUS.UNREVIEWED
            status=article_status
        )
        db.session.add(article)

        article_content = ArticleContent(id=article_id, content=content)
        db.session.add(article_content)

        # TODO 已废弃
        article_statistic = ArticleStatistic(id=article_id)
        db.session.add(article_statistic)

        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return {'message': 'Server has something wrong.'}, 507

        # if not draft:
            # TODO 机器审核
            # TODO 新文章消息推送

        return {'id': article_id}, 201

    def _status(self, value):
        err_msg = 'Invalid status param.'
        try:
            status = int(value)
        except Exception:
            raise ValueError(err_msg)
        if status not in Article.STATUS_ENUM:
            raise ValueError(err_msg)
        return status

    def get(self):
        """
        查询文章列表
        """
        db.session().set_to_read()
        req_parser = RequestParser()
        req_parser.add_argument('status', type=self._status, required=False, location='args', action='append')
        req_parser.add_argument('channel_id', type=self._channel_id, required=False, location='args', action='append')
        req_parser.add_argument('begin_pubdate', type=parser.date, required=False, location='args')
        req_parser.add_argument('end_pubdate', type=parser.date, required=False, location='args')
        req_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        req_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_ARTICLE_PER_PAGE_MIN,
                                                                  constants.DEFAULT_ARTICLE_PER_PAGE_MAX,
                                                                  'per_page'),
                                required=False, location='args')

        # 定制返回值字段，供评论文章接口使用
        req_parser.add_argument('response_type', required=False, location='args')
        args = req_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_ARTICLE_PER_PAGE_MIN

        begin_pubdate = args['begin_pubdate']
        end_pubdate = args['end_pubdate']
        if begin_pubdate and end_pubdate and begin_pubdate > end_pubdate:
            return {'message': 'Invalid pubdate param.'}, 400

        total_count_query = db.session.query(func.count(Article.id)).filter(Article.user_id == g.user_id)
        if args['response_type'] == 'comment':
            # 用于获取评论文章数据
            article_query = Article.query.join(Article.statistic).options(
                load_only(Article.id, Article.title, Article.allow_comment, Article.comment_count),
                contains_eager(Article.statistic).load_only(ArticleStatistic.fans_comment_count)
            ).filter(Article.user_id == g.user_id, Article.status == Article.STATUS.APPROVED)

        elif args['response_type'] == 'statistic':
            # 用于获取统计文章数据
            article_query = Article.query.join(Article.statistic).options(
                load_only(Article.id, Article.title, Article.comment_count),
                contains_eager(Article.statistic)
            ).filter(Article.user_id == g.user_id, Article.status == Article.STATUS.APPROVED)

        else:
            article_query = Article.query.options(load_only(Article.id, Article.title, Article.status, Article.cover,
                                                            Article.ctime))\
                .filter(Article.user_id == g.user_id, Article.status != Article.STATUS.DELETED,
                        Article.status != Article.STATUS.BANNED)

        status = args['status']
        if status:
            total_count_query = total_count_query.filter(Article.status.in_(status))
            article_query = article_query.filter(Article.status.in_(status))

        channel_id = args['channel_id']
        if channel_id:
            total_count_query = total_count_query.filter(Article.channel_id.in_(channel_id))
            article_query = article_query.filter(Article.channel_id.in_(channel_id))

        if begin_pubdate:
            total_count_query = total_count_query.filter(Article.ctime >= begin_pubdate)
            article_query = article_query.filter(Article.ctime >= begin_pubdate)

        if end_pubdate:
            end_pubdate = end_pubdate + timedelta(hours=23, minutes=59, seconds=59)
            total_count_query = total_count_query.filter(Article.ctime <= end_pubdate)
            article_query = article_query.filter(Article.ctime <= end_pubdate)

        # 查询总数
        ret = total_count_query.first()
        total_count = ret[0]
        results = []

        if total_count > 0 and total_count > (page-1)*per_page:
            articles = article_query.order_by(Article.id.desc()).offset((page-1)*per_page).limit(per_page).all()

            if args['response_type'] == 'comment':
                for article in articles:
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'comment_status': article.allow_comment,
                        'total_comment_count': cache_statistic.ArticleCommentCountStorage.get(article.id),
                        'fans_comment_count': article.statistic.fans_comment_count
                    })
            elif args['response_type'] == 'statistic':
                for article in articles:
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'comment_count': article.comment_count,
                        'read_count': cache_statistic.ArticleCommentCountStorage.get(article.id),
                        'like_count': cache_statistic.ArticleLikingCountStorage.get(article.id),
                        'repost_count': article.statistic.repost_count,
                        'collect_count': cache_statistic.ArticleCollectingCountStorage.get(article.id)
                    })
            else:
                for article in articles:
                    results.append({
                        'id': article.id,
                        'title': article.title,
                        'status': article.status,
                        'cover': article.cover,
                        'pubdate': article.ctime.strftime('%Y-%m-%d %H:%M:%S')
                    })

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


class ArticleResource(ArticleResourceBase):
    """
    文章
    """
    def put(self, target):
        """
        修改文章
        """
        req_parser = RequestParser()
        req_parser.add_argument('draft', type=inputs.boolean, required=False, location='args')
        req_parser.add_argument('title', type=inputs.regex(r'.{5,30}'), required=True, location='json')
        req_parser.add_argument('content', type=inputs.regex(r'.+'), required=True, location='json')
        req_parser.add_argument('cover', type=self._cover, required=True, location='json')
        req_parser.add_argument('channel_id', type=self._channel_id, required=True, location='json')
        args = req_parser.parse_args()
        content = args['content']
        cover = args['cover']
        draft = args['draft']

        ret = db.session.query(func.count(Article.id)).filter(Article.id == target, Article.user_id == g.user_id).first()
        if ret[0] == 0:
            return {'message': 'Invalid article.'}, 400

        # 对于自动封面，生成封面
        cover_type = cover['type']
        if cover_type == -1:
            cover = self._generate_article_cover(content)

        # TODO 暂时增加特权帐号，文章直接为审核通过状态
        if draft:
            article_status = Article.STATUS.DRAFT
        else:
            article_status = Article.STATUS.APPROVED if g.user_id == 1 else Article.STATUS.UNREVIEWED

        Article.query.filter_by(id=target).update(dict(
            channel_id=args['channel_id'],
            title=args['title'],
            cover=cover,
            # status=Article.STATUS.DRAFT if draft else Article.STATUS.UNREVIEWED
            status=article_status
        ))

        ArticleContent.query.filter_by(id=target).update(dict(content=content))

        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return {'message': 'Server has something wrong.'}, 507

        # 清除缓存
        cache_user.UserArticlesCache(g.user_id).clear()
        cache_article.ArticleInfoCache(target).clear()
        cache_article.ArticleDetailCache(target).clear()

        # if not draft:
            # TODO 机器审核
            # TODO 新文章消息推送

        return {'id': target}, 201

    def get(self, target):
        """
        获取指定文章
        """
        article = Article.query.join(Article.content)\
            .options(load_only(Article.title, Article.cover, Article.channel_id),
                     contains_eager(Article.content).load_only(ArticleContent.content))\
            .filter(Article.id == target, Article.user_id == g.user_id, Article.status != Article.STATUS.DELETED)\
            .first()

        if article:
            return {
                'id': target,
                'title': article.title,
                'cover': article.cover,
                'channel_id': article.channel_id,
                'content': article.content.content
            }
        else:
            return {}

    def delete(self, target):
        """
        删除文章
        """
        ret = Article.query.filter(Article.id == target,
                                   Article.user_id == g.user_id,
                                   Article.status.in_([Article.STATUS.DRAFT, Article.STATUS.UNREVIEWED,
                                                       Article.STATUS.FAILED]))\
            .update({'status': Article.STATUS.DELETED}, synchronize_session=False)
        db.session.commit()
        if ret == 0:
            return {'message': 'Invalid article.'}, 400

        # TODO 维护ES
        return {'message': 'ok'}, 204
