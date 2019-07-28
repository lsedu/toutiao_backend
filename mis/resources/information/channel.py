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


class ChannelListResource(Resource):
    """
    频道列表
    """
    channel_fields = {
        'channel_id': fields.String(attribute='id'),  # 频道ID
        'name': fields.String(attribute='name'),  # 频道名称
        'is_visible': fields.Integer(attribute='is_visible'),  # 状态: 是否可见
    }

    method_decorators = {
        'get': [mis_permission_required('channel-list-get')],
        'post': [mis_permission_required('channel-list-post')],
    }

    def get(self):
        """
        获取所有频道信息
        """
        args_parser = RequestParser()
        args_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        args_parser.add_argument('per_page', type=inputs.int_range(constants.PER_PAGE_MIN,
                                                                   constants.PER_PAGE_MAX,
                                                                   'per_page'),
                                 required=False, location='args')
        args_parser.add_argument('channel_id', location='args')
        args_parser.add_argument('keyword', location='args')
        args_parser.add_argument('is_visible', location='args')
        args_parser.add_argument('order_by', location='args')

        args = args_parser.parse_args()
        page = constants.DEFAULT_PAGE if args.page is None else args.page
        per_page = constants.DEFAULT_PER_PAGE if args.per_page is None else args.per_page

        channels = Channel.query
        if args.channel_id is not None:
            channels = channels.filter_by(channel_id=args.channel_id)
        if args.is_visible is not None:
            channels = channels.filter_by(is_visible=args.is_visible)
        if args.keyword is not None:
            channels = channels.filter(Channel.name.like('%' + args.keyword + '%'))

        if args.order_by is not None:
            if args.order_by == 'id':
                channels = channels.order_by(Channel.id.asc())
        else:
            channels = channels.order_by(Channel.utime.desc())
        total_count = channels.count()
        channels = channels.offset(per_page * (page - 1)).limit(per_page).all()

        ret = marshal(channels, ChannelListResource.channel_fields, envelope='channels')
        for channel in ret['channels']:
            channel['article_count'] = Article.query.filter_by(channel_id=channel['channel_id']).count()
        ret['total_count'] = total_count

        return ret

    def post(self):
        """
        新增频道
        """
        json_parser = RequestParser()
        json_parser.add_argument('name', required=True, location='json')
        json_parser.add_argument('is_visible', type=inputs.int_range(0, 1), required=True, location='json')
        json_parser.add_argument('sequence', type=inputs.positive, location='json')

        args = json_parser.parse_args()
        if Channel.query.filter_by(name=args.name).first():
            return {'message': '{} already exists'.format(args.name)}, 403

        channel = Channel(name=args.name,
                       is_visible=args.is_visible,
                       sequence=args.sequence if args.sequence is not None else 0,
                        )
        db.session.add(channel)
        db.session.commit()

        return marshal(channel, ChannelListResource.channel_fields), 201


class ChannelResource(Resource):
    """
    频道
    """
    method_decorators = {
        'put': [mis_permission_required('channel-list-put')],
        'delete': [mis_permission_required('channel-list-delete')],
    }

    def put(self, target):
        """
        修改频道
        """
        json_parser = RequestParser()
        json_parser.add_argument('name', required=True, location='json')
        json_parser.add_argument('is_visible', type=inputs.int_range(0, 1), required=True, location='json')
        json_parser.add_argument('sequence', type=inputs.positive, location='json')
        args = json_parser.parse_args()

        channel = Channel.query.filter_by(id=target).first()
        if not channel:
            return {'message': 'Invalid channel id.'}, 400

        if args.name is not None and args.name != channel.name:
            if Channel.query.filter_by(name=args.name).first():
                return {'message': '{} already exists'.format(args.name)}, 403
            channel.name = args.name
        if args.is_visible is not None:
            channel.is_visible = args.is_visible
        if args.sequence is not None:
            channel.sequence = args.sequence
        db.session.add(channel)
        db.session.commit()

        return marshal(channel, ChannelListResource.channel_fields), 201

    def delete(self, target):
        """
        删除频道
        """
        if Article.query.filter_by(channel_id=target).first():
            return {'message': 'Please delete the article first.'}, 400

        Channel.query.filter_by(id=target).delete(synchronize_session=False)
        return {'message': 'OK'}, 204

