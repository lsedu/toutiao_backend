from flask import current_app
from qiniu import Auth, put_file, etag, put_data
import qiniu.config

def upload(file_data):
    # 需要填写你的 Access Key 和 Secret Key
    '''
    QINIU_ACCESS_KEY = 'vvWChY25izwlROAKIHCTCvRcWxFST0lU7rJ9VAO0'
    QINIU_SECRET_KEY = 'txfv38R8rX4lYh0KeB-ZBSLxHlXlU1zJbA730Rhm'
    QINIU_BUCKET_NAME = 'my_toutiao01'
    QINIU_DOMAIN = 'http://puw2c37bg.bkt.clouddn.com/'
    :param file_data:
    :return:
    '''

    access_key = current_app.config["QINIU_ACCESS_KEY"]
    secret_key = current_app.config["QINIU_SECRET_KEY"]
    # 构建鉴权对象
    q = Auth(access_key, secret_key)
    # 要上传的空间
    bucket_name = current_app.config["QINIU_BUCKET_NAME"]





    # 上传后保存的文件名
    # key = 'my-python-logo.png'
    key = None
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)

    ret,info = put_data(token,key,file_data)
    '''Args:
        up_token:         上传凭证
        key:              上传文件名
        data:             上传二进制流
        '''

    return ret["key"]


def upload_test(file_data):

    access_key = 'vvWChY25izwlROAKIHCTCvRcWxFST0lU7rJ9VAO0'
    secret_key = 'txfv38R8rX4lYh0KeB-ZBSLxHlXlU1zJbA730Rhm'
    # 要上传的空间
    bucket_name = 'img02'
    # 构建鉴权对象
    q = Auth(access_key, secret_key)


    # 上传后保存的文件名
    # key = 'my-python-logo.png'
    key = None
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    ret, info = put_data(token, key, file_data)
    return ret["key"]
if __name__ == '__main__':


    import os

    for filename in os.listdir(r'/home/python/toutiao/static/img/'):
        # print(filename)
        with open("/home/python/toutiao/static/img/%s"%filename,"rb") as f:
            file_data =f.read()

        ret=upload_test(file_data)

        print('http://puxgejinx.bkt.clouddn.com/%s'%(ret))