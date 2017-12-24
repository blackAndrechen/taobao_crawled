from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pymongo
import argparse
import re
import requests
import json
import pymongo
from multiprocessing.dummy import Pool

__version__ = "0.2.0"

#获取命令行参数
def get_parser():
    parser = argparse.ArgumentParser(description='search name databasename weatherrank')
    parser.add_argument('-k','--keyword',type=str,help='you need search taobao goods name')
    parser.add_argument('-d','--database',type=str,help='saved to database name')
    parser.add_argument('-r','--rank',type=str,help='whether open func crawl rank')
    parser.add_argument('-v','--version',action='store_true',help='displays the current version of taobao_crawl')
    return parser

#解析命令行参数
def command_line_parser():
    parser = get_parser()
    args = vars(parser.parse_args())
    if args['version']:
        print(__version__)
        return
    if not args['keyword']:
        parser.print_help()
    #爬取淘宝商品
    if args['keyword']:
        #获得要搜索的淘宝商品名字
        goods = args['keyword']
        #保存到数据库的名字
        mongoDB = args['database']
        mongotable = mongoDB + 'table'
        #mongodb配置
        client = pymongo.MongoClient('localhost', 27017)
        dataname = client[mongoDB]
        global table
        #table保存商品
        table = dataname[mongotable]
        #启动商品爬虫
        sumpage = search(goods)
        sumpage = int(re.compile('(\d+)').search(sumpage).group(1))  # 利用正则表达式提取数字，并强制转换为int类型
        for i in range(2, sumpage + 1):
            next_page(i)
        browser.close()
    #爬取商品评论信息
    if args['rank']:
        mongoDB = args['database']
        mongotable = mongoDB + 'rank'
        client = pymongo.MongoClient('localhost', 27017)
        dataname = client[mongoDB]
        global table2,allgoods
        # 读取table中商品信息(itemid,sellid),table2保存评论信息
        table = dataname[args['database']+'table']
        table2 = dataname[mongoDB + 'rank']
        allgoods = []
        for i in table.find({}):
            goodsdic = {'itemid': i['itemid'],
                        'sellerid': i['sellerid']}
            allgoods.append(goodsdic)

        def main(i):
            goods = allgoods[i]
            print('crawl progress {}/{}--->'.format(i, len(allgoods)))
            crawl_rank(goods['itemid'], goods['sellerid'])

        if __name__ == "__main__":
            pool = Pool()
            pool.map(main, [i for i in range(len(allgoods))])

#模拟搜索
def search(goods):
    global browser, wait
    browser = webdriver.Chrome()
    #设置等待变量，方便后面代码书写
    wait = WebDriverWait(browser, 10)
    try:
        browser.get('https://www.taobao.com/')#打开淘宝首页
        tb_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))
        )#等待输入框加载完成
        search_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )#等待搜索按钮加载完成
        tb_input.send_keys(goods)#输入框中传入"商品"
        search_btn.click()#点击搜索
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'))
        )#加载完成，获取页数元素
        get_products(page_number=1)
        return total.text#获取元素中的文本
    except TimeoutException:
        return search(goods)#若发生异常，重新调用自己

#获取商品信息
def get_products(page_number):
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item'))
    )#等待商品信息加载完成，商品信息的CSS选择器分析HTML源码得到
    html = browser.page_source#得到页面HTML源码
    doc = pq(html)#创建PyQuery对象
    items = doc('#mainsrp-itemlist .items .item').items()#获取当前页所有商品信息的html源码
    for item in items:
        product = {
            # 'image':item.find('.pic .img').attr('src'),
            'itemid':item.find('.shop .shopname').attr('data-nid'),
            'sellerid':item.find('.shop .shopname').attr('data-userid'),
            'url':item.find('.title .J_ClickStat').attr('href'),
            'price':item.find('.price').text(),
            'deal':item.find('.deal-cnt').text()[:-3],
            'title':item.find('.title').text(),
            'seller':item.find('.shop').text(),
            'location':item.find('.location').text()
        }
        # save_to_mysql(product)
        save_to_mongoDB(page_number,product)#保存到MongoDB

#翻页函数
def next_page(page_number):
    try:
        page_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input'))
        )#等待翻页输入框加载完成
        confirm_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit'))
        )#等待确认按钮加载完成
        page_input.clear()#清空翻页输入框
        page_input.send_keys(page_number)#传入页数
        confirm_btn.click()#确认点击翻页
        wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number))
        )#确认已翻到page_number页
        get_products(page_number)
    # 若发生异常，重新调用自己
    except TimeoutException:
        next_page(page_number)

def save_to_mongoDB(page_number,product):
    try:
        if table.insert(product):
            print("saved {} page --->".format(page_number), product['title'])
    except Exception:
        print('save {} page failed'.format(page_number), product)


def crawl_rank(itemid, sellerid):
    url = 'https://rate.tmall.com/list_detail_rate.htm?itemId={}&sellerId={}&currentPage={}'
    # 获得商品评论最大页数
    maxpage = get_page(itemid, sellerid)
    for page in range(1, maxpage + 1):
        try:
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'}
            response = requests.get(url.format(itemid, sellerid, page), headers=header)
            html = response.text
            # 将html最前面的几个字符去掉，返回字典型数据
            formaljson = html[15:]
            jsondata = json.loads(formaljson)
            items = jsondata['rateList']
            # 遍历items，保存到mongodb
            for item in items:
                goodsrate = {'date': item['rateDate'],
                             'sku': item['auctionSku'],
                             'usernick': item['displayUserNick'],
                             'content': item['rateContent'],
                             'itemid': itemid}
                save_to_mongo(goodsrate)
        except:
            continue

def save_to_mongo(goodsrate):
    try:
        if table2.insert(goodsrate):
            print('saved MongoDB --->', goodsrate['content'])
    except Exception:
        print('save MongoDB failed', goodsrate['itemid'])

def get_page(itemid, sellerid):
    try:
        url = 'https://rate.tmall.com/list_detail_rate.htm?itemId={}&sellerId={}&currentPage={}'
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'}
        response = requests.get(url.format(itemid, sellerid, 0), headers=header)
        html = response.text
        formaljson = html[15:]
        jsondata = json.loads(formaljson)
        return jsondata['paginator']['lastPage']
    except:
        return get_page(itemid, sellerid)

if __name__ == '__main__':
    command_line_parser()



