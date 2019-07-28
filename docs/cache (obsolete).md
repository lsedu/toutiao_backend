# 1 User Cache

| key            | 类型 | 说明                                                         | 举例                   |
| -------------- | ---- | ------------------------------------------------------------ | ---------------------- |
| user           | zset | 最近活跃的用户<br />用户登录和触发login_required装饰器时更新<br />aps定时任务定时清理，仅保留有限的用户记录 | [{user_id, timestamp}] |
| user:{user_id} | hash | user_id用户的数据缓存，包括手机号、用户名、头像              |                        |



| key                      | 类型 | 说明                   | 举例                     |
| ------------------------ | ---- | ---------------------- | ------------------------ |
| user:following           | zset | 最近缓存的用户关注信息 | [{user_id, timestamp}]   |
| user:{user_id}:following | zset | user_id的关注用户      | [{user_id, update_time}] |

| key                 | 类型 | 说明                   | 举例                     |
| ------------------- | ---- | ---------------------- | ------------------------ |
| user:fans           | zset | 最近缓存的用户关注信息 | [{user_id, timestamp}]   |
| user:{user_id}:fans | zset | user_id的粉丝用户      | [{user_id, update_time}] |

| key                | 类型 | 说明                   | 举例                        |
| ------------------ | ---- | ---------------------- | --------------------------- |
| user:art           | zset | 最近缓存的用户文章数据 | [{user_id, timestamp}]      |
| user:{user_id}:art | zset | user_id的文章          | [{article_id, create_time}] |



# 2 Comment Cache

| key                            | 类型 | 说明                                                         | 举例                                                         |
| ------------------------------ | ---- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| art:comm                       | zset | 热门评论的文章列表<br />获取评论时添加，评论审核时更新缓存<br />aps定时任务定时清理，仅保留有限的评论记录 | [{article_id, timestamp}]                                    |
| art:{article_id}:comm          | zset | article_id文章的评论数据缓存，值为comment_id                 | [{'comment_id',  comment_id}]                                |
| art:{article_id}:comm:figure   | hash | article_id文章的评论数据<br />count字段为评论总数<br />end_id字段为最后时间倒序的最后一个评论id | {"count":0, "end_id": xxx}                                   |
| comm:reply                     | zset | 热门评论的评论列表<br />获取评论时添加，评论审核时更新缓存<br />aps定时任务定时清理，仅保留有限的评论记录 | [{comment_id, timestamp}]                                    |
| comm:{comment_id}:reply        | zset | comment_id评论的评论数据缓存，值为comment_id                 | [{'comment_id',  comment_id}]                                |
| comm:{comment_id}:reply:figure | hash | comment_id文章的评论数据<br />count字段为评论总数<br />end_id字段为最后时间倒序的最后一个评论id | {"count":0, "end_id": xxx}                                   |
| comm:{comment_id}              | hash | 缓存的评论数据                                               | {    'com_id':1,  'aut_id': 0,     'aut_name': '',     'aut_photo': '',     'like_count': 0,     'reply_count': 0,     'pubdate': '',     'content': '',     'is_top': False } |



# 3 Article Cache

| key                     | 类型   | 说明                                  | 举例                      |
| ----------------------- | ------ | ------------------------------------- | ------------------------- |
| art                     | zset   | 记录热门文章id，aps依据此进行定时清理 | [{article_id, timestamp}] |
| ch:{channel_id}:art:top | zset   | 置顶文章                              | [{article_id, sequence}]  |
| art:{article_id}:info   | hash   | 文章的基本信息                        |                           |
| art:{article_id}:detail | string | 文章的内容                            | 'pickled data'            |



# 4 Announcement Cache

| key                        | 类型   | 说明 | 举例                               |
| -------------------------- | ------ | ---- | ---------------------------------- |
| announce                   | zset   |      | [{'pickle data', announcement_id}] |
| announce:{announcement_id} | string |      | 'pickle data'                      |

