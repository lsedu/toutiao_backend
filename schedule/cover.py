from sqlalchemy.orm import load_only
import re
import random
from common import toutiao_app, db
import logging

from models.user import User
from models.news import Article, ArticleContent


logger = logging.getLogger('apscheduler')


def generate_article_cover():
    """
    生成文章封面(处理测试数据专用）
    """
    max = 141428
    with toutiao_app.app_context():
        for article_id in range(1, max+1):
            article = Article.query.options(load_only(Article.cover)).filter_by(id=article_id).first()
            if not article:
                continue
            logging.info('handle {}'.format(article_id))

            if article.cover['type'] > 0:
                continue
            content = ArticleContent.query.filter_by(id=article_id).first()
            if content is None:
                continue
            results = re.findall(r'src=\"http([^"]+)\"', content.content)
            length = len(results)
            if length <= 0:
                continue
            elif length < 3:
                img_url = random.choice(results)
                img_url = 'http' + img_url
                Article.query.filter_by(id=article_id).update({'cover': {'type': 1, 'images': [img_url]}})
                db.session.commit()
            else:
                random.shuffle(results)
                img_urls = results[:3]
                img_urls = ['http' + img_url for img_url in img_urls]
                Article.query.filter_by(id=article_id).update({'cover': {'type': 3, 'images': img_urls}})
                db.session.commit()
