create database toutiao default charset=utf8;
create user toutiao  identified by 'Toutiao123456';
grant all on toutiao.* to 'toutiao'@'%';
flush privileges;
