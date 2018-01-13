from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyquery import PyQuery as pq
from multiprocessing.dummy import Pool
import re,requests,argparse,pymongo,json

__version__ = '0.2.1'

def get_parser(): #获取命令行参数
	parser = argparse.ArgumentParser(description='crawl taobao goods list and all rank')
	parser.add_argument('-k','--keyword',type=str,help='需要爬取的商品名字')
	parser.add_argument('-d','--database',type=str,help='保存到数据库的名字，若无则自动创建')
	parser.add_argument('-r','--rank',type=str,help='是否开启抓取评论功能')
	parser.add_argument('-v','--version',action='store_true',help='版本信息')
	return parser

def command_line_parser(): #解析命令行参数
	parser = get_parser()
	args = vars(parser.parse_args())
	if args['version']:
		print(__version__)
		return
	if not args['database']:
		parser.print_help()
	if args['keyword'] and args['database'] and not args['rank']: #抓取商品列表
		mongodb = args['database'] #设置保存到数据库的名字
		goodstable = mongodb + 'table'#设置数据表名字
		client = pymongo.MongoClient('localhost',27017)
		dataname = client[mongodb]
		global browser,wait,table
		table = dataname[goodstable]
		goods = args['keyword']
		browser = webdriver.PhantomJS()  #注意phantomjs.exe所在的文件夹需要配置到环境变量
		wait = WebDriverWait(browser,10)
		sumpage = search(goods) #搜索商品，模拟点击
		sumpage = int(re.compile('(\d+)').search(sumpage).group(1)) #获得总页数
		for i in range(2, sumpage + 1): #翻页
			next_page(i)
		browser.close()
	if args['database'] and args['rank'] and not args['keyword']: #抓取商品评论信息
		mongodb = args['database']
		goodstable = mongodb + 'table'
		ranktable = mongodb + 'rank'
		client = pymongo.MongoClient('localhost',27017)
		dataname = client[mongodb]
		global table2
		table2 = dataname[ranktable]
		table = dataname[goodstable]
		allgoods = [] #获取数据库中的所有商品的itemid和sellerid
		for i in table.find({}):
			goodsdic = {'itemid': i['itemid'],
            'sellerid': i['sellerid']}
			allgoods.append(goodsdic)
		goods_nums = len(allgoods) #总商品数
		def main(i):
			goods = allgoods[i]
			print('crawl progress {}/{}--->'.format(i, goods_nums))
			crawl_rank(goods['itemid'], goods['sellerid'])

		if __name__ == "__main__": #多线程
			pool = Pool()
			pool.map(main, [i for i in range(len(allgoods))])


def search(goods):     #模拟搜索，返回总页数
	try:
		browser.get('http://www.taobao.com/')
		tb_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))) #等待输入框加载完成
		tb_input.send_keys(goods,Keys.RETURN)   #搜索商品，并模拟回车键确定
		total = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))
		get_products(page_number=0)
		return total.text  #商品总页数
	except TimeoutException:  #超时则重新调用
		return search(goods)

def get_products(page_number):
	wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')))
	doc = pq(browser.page_source)
	items = doc('#mainsrp-itemlist .items .item').items()  #获取当前页所有商品信息的html源码
	for item in items:
		product = {'image':item.find('.pic .img').attr('src'),
            'itemid':item.find('.shop .shopname').attr('data-nid'),
            'sellerid':item.find('.shop .shopname').attr('data-userid'),
            'url':item.find('.title .J_ClickStat').attr('href'),
            'price':item.find('.price').text(),
            'deal':item.find('.deal-cnt').text()[:-3],
            'title':item.find('.title').text(),
            'seller':item.find('.shop').text(),
            'location':item.find('.location').text()}
		save_to_mongo(product,table,page_number)

def next_page(page_number):
	try:
		page_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input')))              #等待翻页输入框加载完成
		confirm_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
		page_input.clear()     #清空翻页输入框
		page_input.send_keys(page_number)    #传入页数
		confirm_btn.click()
		wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number)))                    #确认已翻到page_number页
		get_products(page_number)
	except TimeoutException:    # 若发生异常，重新调用自己
		next_page(page_number)

def crawl_rank(itemid, sellerid):    #itemid和sellerid是抓取商品信息得到的，用来构造评论信息的url
	url = 'https://rate.tmall.com/list_detail_rate.htm?itemId={}&sellerId={}&currentPage={}'
	maxpage = get_page(itemid, sellerid)       # 获得商品评论最大页数
	for page in range(1, maxpage + 1):
		try:
			header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'}
			response = requests.get(url.format(itemid, sellerid, page), headers=header)
			html = '{'+response.text+'}'
			jsondata = json.loads(html)
			items = jsondata['rateDetail']['rateList']     # 遍历items，保存到mongodb
			for item in items:
				goodsrate = {'date': item['rateDate'],
                             'sku': item['auctionSku'],
                             'usernick': item['displayUserNick'],
                             'content': item['rateContent']}
				print(goodsrate['content'])
				save_to_mongo(goodsrate,table2,page_number=-1)
		except:
			continue

def get_page(itemid, sellerid):
	try:
		url = 'https://rate.tmall.com/list_detail_rate.htm?itemId={}&sellerId={}&currentPage={}'
		header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36'}
		response = requests.get(url.format(itemid, sellerid, 0), headers=header)
		html = '{'+response.text+'}'
		jsondata = json.loads(html)
		return jsondata['rateDetail']['paginator']['lastPage']
	except:
		return get_page(itemid, sellerid)

def save_to_mongo(product,mongotable,page_number):
	try:
		if mongotable.insert(product):
			if page_number != -1: 
				print('crawled {} page,saved MongoDB success --->'.format(page_number), product['title'])
			if page_number == -1:
				print('crawl success --->',product['content'])
	except Exception:
		print('save MongoDB failed', product)

if __name__ == "__main__":
	command_line_parser()
