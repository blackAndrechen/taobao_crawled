import requests
import json
import pymongo

#连接数据库，获取itemid和sellerid
client = pymongo.MongoClient('localhost',27017)
dataname = client['tb_kouhon']
table = dataname['goods_info']
allgoods = []
for i in table.find({}):
    goodsdic = {'itemid':i['itemid'],
    'sellerid':i['sellerid']}
    allgoods.append(goodsdic)

#将评论数据保存到table2
table2 = dataname['goods_ratelist']

def crawl_rank(itemid,sellerid):
    url = 'https://rate.tmall.com/list_detail_rate.htm?itemId={}&sellerId={}&currentPage={}'
    #获得商品评论最大页数
    maxpage = get_page(itemid,sellerid)
    for page in range(1,maxpage+1):
        try:
            header = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'}
            response = requests.get(url.format(itemid,sellerid,page),headers= header)
            html = response.text
            #将html最前面的几个字符去掉，返回字典型数据
            formaljson = html[15:]
            jsondata = json.loads(formaljson)
            items = jsondata['rateList']
            #遍历items，保存到mongodb
            for item in items:
                goodsrate = {'date':item['rateDate'],
                             'sku':item['auctionSku'],
                             'usernick':item['displayUserNick'],
                             'content':item['rateContent']}
                save_to_mongo(goodsrate)
        except:
            continue

def save_to_mongo(goodsrate):
    try:
        if table2.insert(goodsrate):
            print('存储到MongoDB成功',goodsrate)
    except Exception:
        print('存储到MongoDB失败',goodsrate)

def get_page(itemid,sellerid):
    try:
        url = 'https://rate.tmall.com/list_detail_rate.htm?itemId={}&sellerId={}&currentPage={}'
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'}
        response = requests.get(url.format(itemid,sellerid,0), headers=header)
        html = response.text
        formaljson = html[15:]
        jsondata = json.loads(formaljson)
        return jsondata['paginator']['lastPage']
    except:
        return get_page(itemid,sellerid)

def main():
    for i in range(len(allgoods)):
        goods = allgoods[i]
        crawl_rank(goods['itemid'],goods['sellerid'])

if __name__ == "__main__":
    main()