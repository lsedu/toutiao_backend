import MySQLdb
import json
import random


client = MySQLdb.Connect(host='172.17.0.136',
                         port=3306,
                         user='toutiao',
                         passwd='Toutiao123456',
                         db='toutiao',
                         charset='utf8')
cursor = client.cursor()

channels = {}
user_ids = [1, 2, 3]

with open('/Users/delron/Downloads/news14w.json', 'r') as f:
    while True:
        l = f.readline()
        if not l:
            break

        data = json.loads(l)
        channel_name = data.get('cate')
        if not channel_name:
            continue

        # 处理类别
        channel_id = channels.get(channel_name)
        if not channel_id:
            sql = 'select channel_id from news_channel where channel_name=%s;'
            count = cursor.execute(sql, args=(channel_name,))
            if count > 0:
                result = cursor.fetchone()
                channel_id = result[0]
                channels[channel_name] = channel_id
            else:
                sql = 'insert into news_channel(channel_name) values(%s);'
                cursor.execute(sql, args=(channel_name,))
                channel_id = cursor.lastrowid
                channels[channel_name] = channel_id
                client.commit()
                print('channel_name={} channel_id={}'.format(channel_name, channel_id))

        # 处理内容
        sql = 'insert into news_article_basic(user_id, channel_id, title, cover, status) ' \
              'values(%(user_id)s, %(channel_id)s, %(title)s, %(cover)s, %(status)s);'

        user_id = random.choice(user_ids)
        status = 2
        cover = '{"type":0, "images":[]}'
        title = data.get('title', '')

        params = {
            'user_id': user_id,
            'channel_id': channel_id,
            'title': title,
            'cover': cover,
            'status': status
        }
        try:
            cursor.execute(sql, args=params)
        except Exception as e:
            client.rollback()
            continue
        article_id = cursor.lastrowid
        sql = 'insert into news_article_content(article_id, content) values(%(article_id)s, %(content)s);' \
              'insert into news_article_statistic(article_id) values(%(article_id)s);'
        try:
            cursor.execute(sql, args={'article_id': article_id, 'content': data.get('content', '')})
        except Exception as e:
            print('user_id={} channel_name={} title={} error:{}'.format(user_id, channel_name, title, e))
            client.rollback()
        else:
            client.commit()
            print('user_id={} channel_name={} article_id={} title={}'.format(user_id, channel_name, article_id, title))

client.commit()
client.close()