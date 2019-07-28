from flask_restful import Resource
from flask import g, current_app
from sqlalchemy.orm import load_only
from flask_restful.reqparse import RequestParser
from flask_restful import inputs
from sqlalchemy.exc import IntegrityError

from utils.decorators import verify_required
from models.user import User
from cache import constants as cache_constants
from utils import parser
from models import db
from cache import user as cache_user
from utils.storage import upload_image


class ProfileResource(Resource):
    """
    用户资料
    """
    method_decorators = [verify_required]

    def get(self):
        """
        获取用户资料
        """
        db.session().set_to_read()
        user = User.query.options(load_only(User.id, User.name, User.mobile, User.profile_photo,
                                            User.introduction, User.email)).filter_by(id=g.user_id).first()
        return {
            'id': user.id,
            'name': user.name,
            'intro': user.introduction,
            'photo': current_app.config['QINIU_DOMAIN'] + (user.profile_photo if user.profile_photo
                                                           else cache_constants.DEFAULT_USER_PROFILE_PHOTO),
            'email': user.email,
            'mobile': user.mobile
        }

    def patch(self):
        """
        编辑用户的信息
        """
        db.session().set_to_write()
        json_parser = RequestParser()
        json_parser.add_argument('name', type=inputs.regex(r'^.{1,7}$'), required=False, location='json')
        json_parser.add_argument('intro', type=inputs.regex(r'^.{0,60}$'), required=False, location='json')
        json_parser.add_argument('email', type=parser.email, required=False, location='json')
        args = json_parser.parse_args()

        user_id = g.user_id
        new_cache_values = {}
        new_user_values = {}
        return_values = {'id': user_id}

        if args.name:
            new_cache_values['name'] = args.name
            new_user_values['name'] = args.name
            return_values['name'] = args.name

        if args.intro:
            new_cache_values['intro'] = args.intro
            new_user_values['introduction'] = args.intro
            return_values['intro'] = args.intro

        if args.email:
            # TODO email 缓存
            new_user_values['email'] = args.email
            return_values['email'] = args.email

        try:
            if new_user_values:
                User.query.filter_by(id=user_id).update(new_user_values)
        except IntegrityError:
            db.session.rollback()
            return {'message': 'User name has existed.'}, 409

        db.session.commit()
        if new_cache_values:
            cache_user.UserProfileCache(user_id).clear()

        return return_values, 201


class PhotoResource(Resource):
    """
    用户图像 （头像，身份证）
    """
    method_decorators = [verify_required]

    def patch(self):
        file_parser = RequestParser()
        file_parser.add_argument('photo', type=parser.image_file, required=False, location='files')
        files = file_parser.parse_args()

        user_id = g.user_id
        new_cache_values = {}
        new_user_values = {}
        return_values = {'id': user_id}

        if files.photo:
            try:
                photo_url = upload_image(files.photo.read())
            except Exception as e:
                current_app.logger.error('upload failed {}'.format(e))
                return {'message': 'Uploading profile photo image failed.'}, 507
            new_cache_values['photo'] = photo_url
            new_user_values['profile_photo'] = photo_url
            return_values['photo'] = current_app.config['QINIU_DOMAIN'] + photo_url

        if new_user_values:
            User.query.filter_by(id=user_id).update(new_user_values)

        db.session.commit()

        if new_cache_values:
            cache_user.UserProfileCache(user_id).clear()

        return return_values, 201
