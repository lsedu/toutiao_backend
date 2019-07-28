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
from models.recommend import *
from utils.decorators import mis_permission_required


class SensitiveWordListResource(Resource):
    """
    敏感词
    """
    word_fields = {
        'id': fields.Integer(attribute='id'),  # 敏感词id
        'word': fields.String(attribute='word'),  # 敏感词
        'weights': fields.Integer(attribute='weights'),  # 权重
        'hold_count': fields.Integer(attribute='hold_count'),  # 拦截次数
        'create_time': fields.DateTime(attribute='ctime', dt_format='iso8601'),  # 创建时间
        'update_time': fields.DateTime(attribute='utime', dt_format='iso8601')  # 更新时间
    }

    method_decorators = {
        'get': [mis_permission_required('sensitive-word-list-get')],
        'post': [mis_permission_required('sensitive-word-list-post')],
    }

    def get(self):
        """
        获取敏感词列表
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('word', location='args')
        args_parser.add_argument('order_by', location='args')

        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        words = SensitiveWord.query

        if args.word is not None:
            words = words.filter(SensitiveWord.word.like('%' + args.word + '%'))
        if args.order_by is not None:
            if args.order_by == 'id':
                words = words.order_by(SensitiveWord.id.asc())
        else:
            words = words.order_by(SensitiveWord.utime.desc())
        total_count = words.count()
        words = words.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(words, SensitiveWordListResource.word_fields, envelope='words')
        ret['total_count'] = total_count

        return ret

    def post(self):
        """
        添加敏感词
        """
        args_parser = RequestParser()
        args_parser.add_argument('word', required=True, location='json')
        args_parser.add_argument('weights', type=inputs.natural, required=True, location='json')

        args = args_parser.parse_args()
        if SensitiveWord.query.filter_by(word=args.word).first():
            return {'message': '{} already exists'.format(args.word)}, 403
        word = SensitiveWord(word=args.word,
                             weights=args.weights,
                             hold_count=0)
        db.session.add(word)
        db.session.commit()
        return marshal(word, SensitiveWordListResource.word_fields), 201


class SensitiveWordResource(Resource):
    method_decorators = {
        'get': [mis_permission_required('sensitive-word-get')],
        'put': [mis_permission_required('sensitive-word-put')],
        'delete': [mis_permission_required('sensitive-word-delete')],
    }

    def get(self, target):
        """
        获取敏感词信息
        :param target: 敏感词id
        :return:
        """
        word = SensitiveWord.query.filter_by(id=target).first()
        if not word:
            return {'message': '{} is not exists'.format(target)}, 403

        return marshal(word, SensitiveWordListResource.word_fields)

    def put(self, target):
        """
        修改敏感词信息
        :param target: 敏感词id
        :return:
        """
        args_parser = RequestParser()
        args_parser.add_argument('word', required=True, location='json')
        args_parser.add_argument('weights', type=inputs.natural, required=True, location='json')

        args = args_parser.parse_args()

        word = SensitiveWord.query.filter_by(id=target).first()
        if not word:
            return {'message': '{} is not exists'.format(target)}, 403
        print(word.word, args.word)
        if args.word is not None and args.word != word.word:
            if SensitiveWord.query.filter_by(word=args.word).first():
                return {'message': '{} already exists'.format(args.word)}, 403
            word.word = args.word
        if args.weights:
            word.weights = args.weights
        word.utime = datetime.now()
        db.session.add(word)
        db.session.commit()

        return marshal(word, SensitiveWordListResource.word_fields), 201

    def delete(self, target):
        """
        删除敏感词信息
        :param target: 敏感词id
        """
        SensitiveWord.query.filter_by(id=target).delete(synchronize_session=False)
        db.session.commit()
        return {}, 204

