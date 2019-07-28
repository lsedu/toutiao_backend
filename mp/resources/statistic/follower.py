from flask_restful import Resource
from sqlalchemy import func
from flask import g

from utils.decorators import verify_required
from models.user import UserProfile, Relation
from models import db


class FollowerGenderStatisticResource(Resource):
    """
    粉丝性别统计
    """
    method_decorators = [verify_required]

    def get(self):

        ret = db.session.query(UserProfile.gender, func.count(UserProfile.gender))\
            .join(UserProfile.followings)\
            .filter(Relation.target_user_id == g.user_id, Relation.relation == Relation.RELATION.FOLLOW)\
            .group_by(UserProfile.gender).all()

        male = 0
        female = 0

        for gender, count in ret:
            if gender == UserProfile.GENDER.MALE:
                male = count
            elif gender == UserProfile.GENDER.FEMALE:
                female = count

        return {'male': male, 'female': female}


class FollowerAgeStatisticResource(Resource):
    """
    粉丝年龄统计
    """
    method_decorators = [verify_required]

    def get(self):

        # ret = db.session.query(UserProfile.)
        pass
