from flask import Blueprint
from flask_restful import Api

from utils.output import output_json
from . import basic, search, sales, read_source

statistics_bp = Blueprint('statistics', __name__)
statistics_api = Api(statistics_bp, catch_all_404s=True)
statistics_api.representation('application/json')(output_json)

# 基本统计
statistics_api.add_resource(basic.StatisticsBasicResource, '/v1_0/statistics_basic',
                      endpoint='StatisticsBasic')


# 关键字搜索统计--分页
statistics_api.add_resource(search.StatisticsSearchResource, '/v1_0/statistics_search',
                      endpoint='StatisticsSearch')

# 关键字搜索统计--总数
statistics_api.add_resource(search.StatisticsSearchTotalResource, '/v1_0/statistics_search_total',
                      endpoint='StatisticsSearchTotal')

# 销售额统计--总数
statistics_api.add_resource(sales.StatisticsSalesTotalResource, '/v1_0/statistics_sales_total',
                      endpoint='StatisticsSalesTotal')

# 阅读来源统计-总数
statistics_api.add_resource(read_source.StatisticsReadSourceTotalResource, '/v1_0/statistics_read_source_total',
                      endpoint='StatisticsReadSourceTotal')

