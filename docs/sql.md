```sql
alter table news_read add update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间';


insert into news_article_statistic(article_id) select article_id from news_article_basic;


alter table news_channel add `sequence` int(11) unsigned NOT NULL DEFAULT '0' COMMENT '序号';
alter table news_channel add `is_visible` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否可见';

alter table news_user_channel add `sequence` int(11) unsigned NOT NULL DEFAULT '0' COMMENT '序号';

alter table user_profile drop column introduction;

alter table user_basic add `introduction` varchar(50) NULL COMMENT '简介';

alter table user_basic modify `introduction` varchar(50) NULL COMMENT '简介';

alter table user_basic add `certificate` varchar(30) NULL COMMENT '认证';

alter table user_profile drop column id_card;
alter table user_profile add `id_number` varchar(20) NULL COMMENT '身份证号';
alter table user_profile add `id_card_front` varchar(128) NULL COMMENT '身份证正面';
alter table user_profile add `id_card_back` varchar(128) NULL COMMENT '身份证背面';
alter table user_profile add `id_card_handheld` varchar(128) NULL COMMENT '手持身份证';

alter table user_basic add `is_verified` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否实名认证，0-不是，1-是';


alter table news_article_statistic add `fans_comment_count` int(11) unsigned NOT NULL DEFAULT '0' COMMENT '粉丝评论数';

alter table news_article_basic add `allow_comment` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否允许评论，0-不允许，1-允许';

```

db.session.commit 与 update_cache 的重叠。。