from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from flask import g, current_app
from redis.exceptions import RedisError

from . import constants
from cache import article as cache_article
from cache import user as cache_user
from models.user import Search
from models import db


class SuggestionResource(Resource):
    """
    联想建议
    """
    def get(self):
        """
        获取联想建议
        """
        qs_parser = RequestParser()
        qs_parser.add_argument('q', type=inputs.regex(r'^.{1,50}$'), required=True, location='args')
        args = qs_parser.parse_args()
        q = args.q

        query = {
            'from': 0,
            'size': 10,
            '_source': False,
            'suggest': {
                'word-completion': {
                    'prefix': q,
                    'completion': {
                        'field': 'suggest'
                    }
                }
            }
        }
        ret = current_app.es.search(index='completions', body=query)
        options = ret['suggest']['word-completion'][0]['options']
        if not options:
            query = {
                'from': 0,
                'size': 10,
                '_source': False,
                'suggest': {
                    'text': q,
                    'word-phrase': {
                        'phrase': {
                            'field': '_all',
                            'size': 1,
                            'direct_generator': [{
                                'field': '_all',
                                'suggest_mode': 'always'
                            }]
                        }
                    }
                }
            }
            ret = current_app.es.search(index='articles', doc_type='article', body=query)
            options = ret['suggest']['word-phrase'][0]['options']

        results = []
        for option in options:
            if option['text'] not in results:
                results.append(option['text'])

        return {'options': results}


class SearchResource(Resource):
    """
    搜索结果
    """
    def get(self):
        """
        获取搜索结果
        """
        if g.use_token and not g.user_id:
            return {'message': 'Token has some errors.'}, 401

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
                        {'term': {'status': {'value': 2}}}
                    ]
                }
            }
        }
        ret = current_app.es.search(index='articles', doc_type='article', body=query)

        total_count = ret['hits']['total']

        results = []

        hits = ret['hits']['hits']
        for result in hits:
            article_id = int(result['_id'])
            article = cache_article.ArticleInfoCache(article_id).get()
            if article:
                results.append(article)

        # Record user search history
        if g.user_id and page == 1:
            try:
                cache_user.UserSearchingHistoryStorage(g.user_id).save(q)
            except RedisError as e:
                current_app.logger.error(e)

        # Add new es index doc
        if total_count and page == 1:
            query = {
                '_source': False,
                'query': {
                    'match': {
                        'suggest': q
                    }
                }
            }
            ret = current_app.es.search(index='completions', doc_type='words', body=query)
            if ret['hits']['total'] == 0:
                doc = {
                    'suggest': {
                        'input': q,
                        'weight': constants.USER_KEYWORD_ES_SUGGEST_WEIGHT
                    }
                }
                try:
                    current_app.es.index(index='completions', doc_type='words', body=doc)
                except Exception:
                    pass

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}
