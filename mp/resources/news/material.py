from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from flask import current_app, g
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import load_only
from flask_restful import inputs
from sqlalchemy import func
import math

from utils.decorators import verify_required
from utils import parser
from utils.storage import upload_image
from models.user import Material
from models import db
from . import constants


class ImageListResource(Resource):
    """
    图片资源
    """
    method_decorators = [verify_required]

    def post(self):
        """
        上传图片文件
        """
        req_parser = RequestParser()
        req_parser.add_argument('image', type=parser.image_file, required=True, location='files')
        file = req_parser.parse_args()

        user_id = g.user_id

        try:
            image_key = upload_image(file['image'].read())
        except Exception as e:
            current_app.logger.error('upload failed {}'.format(e))
            return {'message': 'Uploading profile photo image failed.'}, 507

        # TODO 图片默认审核通过
        query = insert(Material).values(
            user_id=user_id,
            type=Material.TYPE.IMAGE,
            hash=image_key,
            url=image_key,
            status=Material.STATUS.APPROVED
        ).on_duplicate_key_update(status=Material.STATUS.APPROVED)

        db.session.execute(query)
        db.session.commit()

        material = Material.query.options(load_only(Material.id, Material.url))\
            .filter_by(user_id=user_id, hash=image_key).first()
        return {'id': material.id, 'url': current_app.config['QINIU_DOMAIN'] + material.url}, 201

    def get(self):
        """
        查询图片
        """
        req_parser = RequestParser()
        req_parser.add_argument('collect', type=inputs.boolean, required=False, location='args')
        req_parser.add_argument('page', type=inputs.positive, required=False, location='args')
        req_parser.add_argument('per_page', type=inputs.int_range(1,
                                                                  constants.DEFAULT_IMAGE_PER_PAGE_MAX,
                                                                  'per_page'),
                                required=False, location='args')
        args = req_parser.parse_args()
        collect = args['collect']
        page = 1 if args['page'] is None else args['page']
        per_page = args.per_page if args.per_page else constants.DEFAULT_IMAGE_PER_PAGE

        resp = {'total_count': 0, 'page': page, 'per_page': per_page, 'results': []}
        # 查询总数
        total_query = db.session.query(func.count(Material.id)).filter(Material.user_id == g.user_id,
                                                                       Material.status != Material.STATUS.DELETED)
        if collect:
            total_query = total_query.filter_by(is_collected=True)
        ret = total_query.first()
        total_count = ret[0]
        if total_count == 0 or page > math.ceil(total_count/per_page):
            return resp

        query = Material.query.options(load_only(Material.id, Material.url, Material.is_collected))\
            .filter(Material.user_id == g.user_id, Material.status != Material.STATUS.DELETED)
        if collect:
            query = query.filter_by(is_collected=True)

        materials = query.order_by(Material.is_collected.desc(), Material.ctime.desc())\
            .offset((page-1)*per_page).limit(per_page).all()
        results = []

        for material in materials:
            results.append(dict(
                id=material.id,
                url=current_app.config['QINIU_DOMAIN'] + material.url,
                is_collected=material.is_collected
            ))

        resp['total_count'] = total_count
        resp['results'] = results
        return resp


class ImageResource(Resource):
    """
    图片资源
    """
    method_decorators = [verify_required]

    def put(self, target):
        """
        修改收藏状态
        """
        req_parser = RequestParser()
        req_parser.add_argument('collect', type=inputs.boolean, required=True, location='json')
        args = req_parser.parse_args()
        collect = args['collect']
        query = Material.query.filter_by(id=target, user_id=g.user_id, status=Material.STATUS.APPROVED)
        if collect:
            query.update({'is_collected': True})
        else:
            query.update({'is_collected': False})
        db.session.commit()
        return {'id': target, 'collect': collect}, 201

    def delete(self, target):
        """
        删除图片
        """
        Material.query.filter_by(id=target, user_id=g.user_id, type=Material.TYPE.IMAGE)\
            .update({'status': Material.STATUS.DELETED, 'is_collected': False})
        db.session.commit()

        return {'message': 'OK'}, 204

