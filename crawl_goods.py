import re
from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pymongo
import pymysql

#config
goods = '口红'
mysqlDB = 'tb'
mongoDB = 'tb_kouhon'
mongotable = 'goods_info'


conn = pymysql.connect(host='localhost',
                       port=3306,
                       user='root',
                       password='',
                       db=mysqlDB,
                       charset='utf8mb4')
cursor = conn.cursor()

client = pymongo.MongoClient('localhost',27017)
dataname = client[mongoDB]
table = dataname[mongotable]

browser = webdriver.Chrome()
#等待变量
wait = WebDriverWait(browser,10)

#模拟搜索
def search():
    try:
        browser.get('https://www.taobao.com/')#打开淘宝首页
        tb_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))
        )#等待输入框加载完成
        search_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )#等待搜索按钮加载完成
        tb_input.send_keys(goods)#输入框中传入“美食”
        search_btn.click()#点击搜索
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'))
        )#加载完成，获取页数元素
        get_products()
        return total.text#获取元素中的文本
    except TimeoutException:
        return search()#若发生异常，重新调用自己

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
        get_products()
    except TimeoutException:
        next_page(page_number)#若发生异常，重新调用自己

#获取商品信息
def get_products():
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
        print(product)
        # save_to_mysql(product)
        # save_to_mongoDB(product)#保存到MongoDB

#保存到MongoDB
def save_to_mongoDB(product):
    try:
        if table.insert(product):
            print('存储到MongoDB成功',product)
    except Exception:
        print('存储到MongoDB失败',product)

def save_to_mysql(product):
    sql = '''INSERT INTO tb_inf(itemid,sellerid,url,price,deal,title,seller,location) VALUES (%s,%s,"%s","%s",%s,"%s","%s","%s")'''
    try:
        cursor.execute(sql % (product['itemid'],product['sellerid'],product['url'],product['price'],product['deal'],product['title'],product['seller'],product['location']))
        conn.commit()
        print('save to mysql successed',product)
    except:
        conn.rollback()

def main():
    total = search()#获取商品页数，字符串类型
    total = int(re.compile('(\d+)').search(total).group(1))#利用正则表达式提取数字，并强制转换为int类型
    for i in range(2, total+1):
        next_page(i)
    conn.close()
    browser.close()

if __name__ == '__main__':
    main()