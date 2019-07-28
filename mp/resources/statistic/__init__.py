from flask import Blueprint
from flask_restful import Api

from . import follower
from utils.output import output_json

statistic_bp = Blueprint('statistic', __name__)
statistic_api = Api(statistic_bp, catch_all_404s=True)
statistic_api.representation('application/json')(output_json)


statistic_api.add_resource(follower.FollowerGenderStatisticResource, '/v1_0/statistics/followers/gender',
                           endpoint='FollowerGenderStatistic')

