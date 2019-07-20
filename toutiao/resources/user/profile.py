from flask import g, current_app
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from models import db
from models.user import User
from utils.QiNiuStorage import upload
from utils.decorators import login_required
from utils.parser import image_file


class PhotoResource(Resource):  #/v1_0/user/photo
    #处理修改头像的请求处理
    # 登录状态下可以修改头像，权限
    method_decorators = [login_required]
    def patch(self):
        #上传头像，保存头像名称

        #1，获取参数、校验参数
        rp = RequestParser()
        rp.add_argument("photo",type=image_file,required=True,location="files")
        #image_file 来自utils.parser ，用来判断文件是否是图片
        req = rp.parse_args()

        #2，业务处理，上传图片数据至七牛云
        file_name = upload(req.photo.read())

        #3，保存文件名至数据库 update from user_profile set profile_photo=xxx where user_id =xx
        # User.query.filter(User.id == g.user_id).update({"User.profile_photo":file_name} )#强制登录时g 中已经有user_id
        User.query.filter(User.id == g.user_id).update({"profile_photo":file_name} )#强制登录时g 中已经有user_id
        db.session.commit()
        #返回数据

        photo_url = current_app.config["QINIU_DOMAIN"] + file_name
        return {"photo_url":photo_url}




