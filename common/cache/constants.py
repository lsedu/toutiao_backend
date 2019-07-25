import random

class DataTTLBase(object):
    TTL = 7200  # 60*60*2
    MAX_DELTA = 600  # 60*10
    @classmethod #类方法
    def get_value(cls):
        return cls.TTL + random.randint(cls.MAX_DELTA)

class UserCacheDataTTL(DataTTLBase):
    pass

class UserNotExistsTTL(DataTTLBase):
    TTL = 6000 #60*10
    MAX_DELTA = 60
