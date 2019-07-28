from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from sqlalchemy.orm import load_only
from flask import g, current_app
from sqlalchemy import func

from utils.decorators import verify_required
from models.user import Relation, User
from . import constants
from cache import constants as cache_constants
from models import db


class FollowerListResource(Resource):
    """
    粉丝
    """
    method_decorators = [verify_required]

    def get(self):
        """
        获取粉丝列表
        """
        req_parser = RequestParser()
        req_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        req_parser.add_argument('per_page', type=inputs.int_range(constants.DEFAULT_FOLLOWER_PER_PAGE_MIN,
                                                                  constants.DEFAULT_FOLLOWER_PER_PAGE_MAX,
                                                                  'per_page'),
                                required=False, location='args')

        args = req_parser.parse_args()
        page = 1 if args.page is None else args.page
        per_page = args.per_page if args.per_page else constants.DEFAULT_FOLLOWER_PER_PAGE_MIN

        # 总量查询
        ret = db.session.query(func.count(Relation.id)).filter(Relation.target_user_id == g.user_id,
                                                               Relation.relation == Relation.RELATION.FOLLOW).first()
        total_count = ret[0]
        results = []

        if total_count > 0 and (page-1)*per_page < total_count:
            followers = User.query.join(User.followings).options(load_only(User.id, User.name, User.profile_photo))\
                .filter(Relation.target_user_id == g.user_id, Relation.relation == Relation.RELATION.FOLLOW)\
                .order_by(Relation.utime.desc()).offset((page-1)*per_page).limit(per_page).all()

            for follower in followers:
                results.append(dict(
                    id=follower.id,
                    name=follower.name,
                    photo=current_app.config['QINIU_DOMAIN'] + (follower.profile_photo if follower.profile_photo
                                                                else cache_constants.DEFAULT_USER_PROFILE_PHOTO)
                ))

        return {'total_count': total_count, 'page': page, 'per_page': per_page, 'results': results}


