# 淘宝爬虫
###### 利用selenium抓取淘宝商品列表
###### 利用requests抓取商品评论
###### 将保存数据到mysql和mongodb


#### 抓取商品的关键字
* 商品的id
* 店铺id
* 商品的url
* 商品价格
* 商品的销量
* 商品的名称
* 店铺名字
* 店铺地址


#### 抓取评论的关键字
* 用户的id
* 用户购买的商品分类
* 用户的评论


#### 抓取原理
* 利用selenium模拟访问，获取指定商品的总页数，然后分别获取每页的商品信息，并保存到数据库
* 利用抓取到的商品信息，用商品id和店铺id构造url访问得到评论的json数据，利用多线程，将格式化的数据保存到数据库

### 运行环境
* python3
* windows10

### 前置库
* requests
* selenium
* pyquery
* pymongo

### 使用方法
将文件下载到本地，cmd进入该文件夹
![](https://github.com/blackAndrechen/taobao_crawled/blob/master/picture/1.PNG)
参数解释
* -h 帮助
* -k 需要爬取的商品名称
* -d 需要保存到的数据库名称（保存到mongodb,程序自动建立数据库）
* -v 版本信息

### 示例
![](picture\2.png)

### 数据库信息
![](picture\3.png)