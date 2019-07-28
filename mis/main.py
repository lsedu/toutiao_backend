# export FLASK_APP
# export FLASK_ENV
# flask run
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'common'))

# test
from utils.gt3.geetest import GeetestLib
from flask import session, request, render_template
import json




from flask import jsonify


from . import create_app
from settings.default import MisDefaultConfig


app = create_app(MisDefaultConfig, enable_config_file=True)


@app.route('/')
def route_map():
    """
    主视图，返回所有视图网址
    """
    rules_iterator = app.url_map.iter_rules()
    return jsonify({rule.endpoint: rule.rule for rule in rules_iterator if rule.endpoint not in ('route_map', 'static')})

# pc_geetest_id = app.config['GEETEST_ID']
# pc_geetest_key = app.config['GEETEST_KEY']

# @app.route('/pc-geetest/register', methods=["GET"])
# def get_pc_captcha():
#     user_id = 'test'
#     print('test')
#     gt = GeetestLib(pc_geetest_id, pc_geetest_key)
#     status = gt.pre_process(user_id)
#     session[gt.GT_STATUS_SESSION_KEY] = status
#     session["user_id"] = user_id
#     response_str = gt.get_response_str()
#     return json.dumps(response_str)
#
# @app.route('/mobile-geetest/register', methods=["GET"])
# def get_mobile_captcha():
#     user_id = 'test'
#     gt = GeetestLib(pc_geetest_id, pc_geetest_key)
#     status = gt.pre_process(user_id)
#     session[gt.GT_STATUS_SESSION_KEY] = status
#     session["user_id"] = user_id
#     response_str = gt.get_response_str()
#     return response_str
#
# @app.route('/pc-geetest/validate', methods=["POST"])
# def pc_validate_captcha():
#     gt = GeetestLib(pc_geetest_id, pc_geetest_key)
#     challenge = request.form[gt.FN_CHALLENGE]
#     validate = request.form[gt.FN_VALIDATE]
#     seccode = request.form[gt.FN_SECCODE]
#     status = session[gt.GT_STATUS_SESSION_KEY]
#     user_id = session["user_id"]
#     if status:
#         result = gt.success_validate(challenge, validate, seccode, user_id)
#     else:
#         result = gt.failback_validate(challenge, validate, seccode)
#     result = "<html><body><h1>登录成功</h1></body></html>" if result else "<html><body><h1>登录失败</h1></body></html>"
#     return result
#
# @app.route('/pc-geetest/ajax_validate', methods=["POST"])
# def pc_ajax_validate():
#     gt = GeetestLib(pc_geetest_id,pc_geetest_key)
#     challenge = request.form[gt.FN_CHALLENGE]
#     validate = request.form[gt.FN_VALIDATE]
#     seccode = request.form[gt.FN_SECCODE]
#     status = session[gt.GT_STATUS_SESSION_KEY]
#     user_id = session["user_id"]
#     if status:
#         result = gt.success_validate(challenge, validate, seccode, user_id,data='',userinfo='')
#     else:
#         result = gt.failback_validate(challenge, validate, seccode)
#     result = {"status":"success"} if result else {"status":"fail"}
#     return json.dumps(result)
#
# @app.route('/mobile-geetest/ajax_validate', methods=["POST"])
# def mobile_ajax_validate():
#     gt = GeetestLib(pc_geetest_id, pc_geetest_key)
#     challenge = request.form[gt.FN_CHALLENGE]
#     validate = request.form[gt.FN_VALIDATE]
#     seccode = request.form[gt.FN_SECCODE]
#     status = session[gt.GT_STATUS_SESSION_KEY]
#     user_id = session["user_id"]
#     if status:
#         result = gt.success_validate(challenge, validate, seccode, user_id,data='',userinfo='')
#     else:
#         result = gt.failback_validate(challenge, validate, seccode)
#     result = {"status":"success"} if result else {"status":"fail"}
#     return json.dumps(result)

# print(app.url_map)

# @app.route('/')
# def login():
#     return render_template('login.html')

# @app.route('/api.html')
# def misapi():
#     return render_template('misAPI.html')
