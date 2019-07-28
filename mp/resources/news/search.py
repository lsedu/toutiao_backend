from flask_restful import Resource
from flask import current_app, g
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from sqlalchemy.orm import load_only

from utils.decorators import verify_required
from . import constants
from models.news import Article


class SearchResource(Resource):
    """
    搜索结果
    """
    method_decorators = [verify_required]

    def get(self):
        """
        获取搜索结果
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('q', type=inputs.regex(r'^.{1,50}$'), required=True, location='args')
        qs_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        qs_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_SEARCH_PER_PAGE_MIN,
                                                                 constants.DEFAULT_SEARCH_PER_PAGE_MAX,
                                                                 'per_page'),
                               required=False, location='args')
        args = qs_parser.parse_args()
        q = args.q
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_SEARCH_PER_PAGE_MIN

        # Search from Elasticsearch
        query = {
            'from': (page-1)*per_page,
            'size': per_page,
            '_source': False,
            'query': {
                'bool': {
                    'must': [
                        {'match': {'_all': q}}
                    ],
                    'filter': [
                        {'term': {'user_id': {'value': g.user_id}}}
                    ],
                    'must_not': [
                        {'term': {'status': {'value': Article.STATUS.DELETED}}}
                    ]
                }
            }
        }
        ret = current_app.es.search(index='articles', doc_type='article', body=query)

        total_count = ret['hits']['total']

        results = []

        hits = ret['hits']['hits']
        if len(hits) > 0:
            article_id_list = [hit['_id'] for hit in hits]
            # TODO 审核拒绝原因
            articles = Article.query.options(load_only(Article.id, Article.title, Article.status, Article.cover, Article.ctime))\
                .filter(Article.id.in_(article_id_list), Article.user_id == g.user_id).all()

            for article in articles:
                results.append({
                    'id': article.id,
                    'title': article.title,
                    'status': article.status,
                    'cover': article.cover,
                    'pubdate': article.ctime.strftime('%Y-%m-%d %H:%M:%S')
                })

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}
