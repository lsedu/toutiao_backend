# from apscheduler.schedulers.background import BackgroundScheduler
#
# #1,创建定时任务的调度器对象
# scheduler = BackgroundScheduler()
#
# #2,定义定时任务
# def my_job(param1,param2):
#     pass
#
# #3,向调度器中添加定时任务
# scheduler.add_job(my_job,'date',args=[100,'python'])
#
# #4,启动定时任务调度器工作
# scheduler.start()


#调度器高度程序
from apscheduler.schedulers.blocking import BlockingScheduler
#作为独立进程时使用：
scheduler = BlockingScheduler()
scheduler.start()  #此处程序会发生阻塞

#在框架中使用
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.start() #此处不会发生阻塞


#执行器执行者
from apscheduler.executors.pool import ThreadPoolExecutor
# ThreadPoolExecutor(max_workers)
ThreadPoolExecutor(20)

