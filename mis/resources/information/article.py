from flask_restful import Resource
from flask import request, current_app, g, session
from flask_restful.reqparse import RequestParser
from flask_restful import inputs, fields, marshal
from datetime import datetime, timedelta
from sqlalchemy.orm import load_only
from sqlalchemy import or_

from . import constants
from utils import parser
from models import db
from models.news import *
from utils.decorators import mis_permission_required


class ArticleListResource(Resource):
    """
    文章列表管理
    """
    article_fields = {
        'article_id': fields.Integer(attribute='id'), # 文章id
        'title': fields.String(attribute='title'),  # 文章名称
        'name': fields.String(attribute='user.name'),  # 作者
        'channel_name': fields.String(attribute='channel.name'),  # 所属频道
        'comment_count': fields.Integer(attribute='comment_count'),  # 评论数
        'update_time': fields.DateTime(attribute='ctime', dt_format='iso8601'),  # 更新时间
        'status': fields.Integer(attribute='status'),  # 状态
    }

    method_decorators = {
        'get': [mis_permission_required('article-list-get')],
        'put': [mis_permission_required('article-list-put')],
    }

    def get(self):
        """
        获取文章列表
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('title', location='args')
        args_parser.add_argument('channel', location='args')
        args_parser.add_argument('status_list', location='args')
        args_parser.add_argument('begin', type=parser.date_time, location='args')
        args_parser.add_argument('end', type=parser.date_time, location='args')
        args_parser.add_argument('order_by', location='args')

        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        articles = Article.query
        if args.title is not None:
            articles = articles.filter(Article.title.like('%' + args.title + '%'))
        if args.channel is not None:
            channels = Channel.query.filter(Channel.name.like('%' + args.channel + '%')).all()
            channel_ids = [i.id for i in channels]
            articles = articles.filter(Article.channel_id.in_(channel_ids))

        if args.status_list is not None:
            try:
                status_list = [int(i) for i in args.status_list.split(',')]
            except:
                return {'message': 'status_list parameter error.'}, 403
            articles = articles.filter(Article.status.in_(status_list))

        if args.begin and args.end and args.end >= args.begin:
            articles = articles.filter(Article.ctime.between(args.begin, args.end))

        if args.order_by is not None:
            if args.order_by == 'id':
                articles = articles.order_by(Article.id.asc())
        else:
            articles = articles.order_by(Article.ctime.desc())
        total_count = articles.count()
        articles = articles.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(articles, ArticleListResource.article_fields, envelope='articles')
        ret['total_count'] = total_count

        return ret

    def put(self):
        """
        批量修改文章状态
        :return:
        """
        json_parser = RequestParser()
        json_parser.add_argument('reject_reason', location='json')
        json_parser.add_argument('status', type=inputs.int_range(1, 6), required=True, location='json')
        json_parser.add_argument('article_ids', action='append', type=inputs.positive,
                                 required=True, location='json')
        args = json_parser.parse_args()
        articles = Article.query.filter(Article.id.in_(args.article_ids)).all()
        need_kafka_send_msgs = []
        need_rebuild_es_indexes = []
        for article in articles:
            if args.status == Article.STATUS.BANNED:
                # 封禁
                if article.status != Article.STATUS.APPROVED:
                    return {'message': '"%s" 文章不是审核状态, 不能封禁' % article.title}, 403
            elif args.status == 6:
                # 解封
                if article.status != Article.STATUS.BANNED:
                    return {'message': '"%s" 文章不是封禁状态, 不能解封' % article.title}, 403
                article.status = Article.STATUS.APPROVED
            elif args.status == Article.STATUS.APPROVED:
                # 通过审核
                if article.status != Article.STATUS.UNREVIEWED:
                    return {'message': '"%s" 文章不是待审核状态, 不能通过审核' % article.title}, 403
                article.review_time = datetime.now()
                article.reviewer_id = g.administrator_id

                # 记录需要kafka推送的消息
                need_kafka_send_msgs.append('{},{}'.format(article.channel_id, article.id))
                # 记录需要es添加索引
                need_rebuild_es_indexes.append(article)

            elif args.status == Article.STATUS.FAILED:
                # 审核失败(驳回)
                if article.status != Article.STATUS.UNREVIEWED:
                    return {'message': '"%s" 文章不是待审核状态, 不能驳回' % article.title}, 403
                article.reviewer_id = g.administrator_id
                article.review_time = datetime.now()
                article.reject_reason = args.reject_reason if args.reject_reason else '系统审核'
            elif args.status == Article.STATUS.DELETED:
                # 删除
                article.delete_time = datetime.now()
            else:
                return {'message': '错误的状态操作'}, 403
            article.status = args.status if args.status != 6 else Article.STATUS.APPROVED
            db.session.add(article)
        db.session.commit()

        # 文章通过审核，kafka推送消息给推荐系统
        for msg in need_kafka_send_msgs:
            current_app.kafka_producer.send('new-article', msg.encode())

        # 添加ES索引
        for article in need_rebuild_es_indexes:
            doc = {
                'article_id': article.id,
                'user_id': article.user_id,
                'title': article.title,
                'content': article.content.content,
                'status': article.status,
                'create_time': article.ctime
                }
            try:
                current_app.es.index(index='articles', doc_type='article', body=doc, id=article.id)
            except Exception as e:
                current_app.logger.error(e)

        return {'message': 'OK'}, 201


class ArticleResource(Resource):
    method_decorators = {
        'get': [mis_permission_required('article-get')],
    }

    def get(self, target):
        # 获取文章完整信息
        article = Article.query.filter_by(id=target).first()
        if not article:
            return {'messaget': 'article is not exits.'}
        ret = marshal(article, ArticleListResource.article_fields)
        ret['content'] = article.content.content
        return ret

