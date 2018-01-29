#!/usr/bin/python
#coding=utf-8

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

import sys

import smtplib  
from email.mime.text import MIMEText  


class Ticket(object):
	''' doc for class Ticket'''
	# username and password
	username = u'xxx'
	password = u'xxx'

	# start and terminal
	start = u"%u6ED5%u5DDE%u4E1C%2CTEK"
	terminal = u"%u4E0A%u6D77%2CSHH"

	# date, format: 2018-02-24, the front has high priority
	dates = [u'2018-02-24', u'2018-02-23', u'2018-02-25', u'2018-02-22']

	# choose trains accroding to the id, the front has high priority
	trains = [2, 4, 5, 7, 8, 9, 10, 11, -2, -3]

	# choose passengers, no more than 5: [order, is_student, student_ticket]
	passengers = [[0, 1, 1],
				  [3, 1, 1],
				  [11, 1, 1]]

	# choose seat type according to the dict below, the front has hign priority
	# Warning: the index 3 may get some problem in the process of choose seat
	seats = [2, 6]

	# all seat type, the 9th is actually 无座
	seat_types = {0: u'商务座', 1: u'一等座', 2: u'二等座', 3: u'高级软卧',  4: u'软卧', 5: u'动卧',  6: u'硬卧', 7: u'软座', 8: u'硬座', 9: u'硬座'}

	# the query conut
	count = 0

	# mail settings
	mailto_list=['xxx@qq.com']           #收件人(列表)  
	mail_host="smtp.163.com"            #使用的邮箱的smtp服务器地址，这里是163的smtp地址
	mail_user="xxx@163.com"                 #用户名  
	mail_pass="xxx"                     #密码  

	def __init__(self):
		options = Options()
		options.add_argument("--headless")
		self.browser = webdriver.Chrome(chrome_options=options)


	def login(self):
		print '[INFO] login...'
		self.browser.get('https://kyfw.12306.cn/otn/login/init')
	
		elem = self.browser.find_element_by_id('username')
		elem.send_keys(self.username)
		elem = self.browser.find_element_by_id('password')
		elem.send_keys(self.password)
		
		print '[INFO] get captcha...'
		elem = self.browser.find_element_by_class_name('touclick-image')
		self.browser.save_screenshot('./captcha.png')

		s = raw_input('please check the screenshot and input the image to be selected (0~7, Separated by empty char):\n')
		s = s.split()
		for i in s:
			i = int(i)
			raw = int(i / 4)
			col = int(i % 4)
			ActionChains(self.browser).move_to_element_with_offset(elem, 40 + 75*col, 80 + 80*raw).click().perform()

		print '[INFO] logging...'
		elem = self.browser.find_element_by_id('loginSub')
		elem.click()

		try:
			WebDriverWait(self.browser, 8).until(expected_conditions.title_contains(u'12306'));
			print '[INFO] login successfully.'
			return 0
		except:
			print '[FATAL] login failed!'
			return 1

	def check_ticket(self):
		self.browser.add_cookie({'name': '_jc_save_fromStation', 'value': self.start})
		self.browser.add_cookie({'name': '_jc_save_toStation', 'value': self.terminal})

		print '[INFO] checking ticket...'

		while len(self.passengers) > 0:
			for date in self.dates:
				self.count += 1
				sys.stdout.write('[INFO]' + ' count: ' + str(self.count) + ', query date: ' + date + '\r')
				sys.stdout.flush()
				self.browser.add_cookie({'name': '_jc_save_fromDate', 'value': date})
				self.browser.get('https://kyfw.12306.cn/otn/leftTicket/init')

				elem = self.browser.find_element_by_id('query_ticket')
				elem.click()
				
				try:
					WebDriverWait(self.browser, 8).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, 'no-br')))
				except:
					self.browser.delete_cookie('_jc_save_fromDate')
					continue

				tickets = self.browser.find_element_by_id('queryLeftTable').find_elements_by_tag_name('tr')
				order_buttons = self.browser.find_elements_by_class_name('no-br')

				flag = False
				for i in self.trains:
					left = tickets[i * 2].find_elements_by_tag_name('td')
					for j in self.seats:
						if left[j + 1].text != '--' and left[j + 1].text != u'无':
							if left[j + 1].text == u'有' or int(left[j + 1].text) >= len(self.passengers):
								flag = True
								order_buttons[i].click()
								if self.submit_order(j):
									self.passengers = []
									print '[^O^] submit successfully! send mail...'
									if self.send_mail("去支付吧", "去12306往网站支付吧"):
										print 'done!'
									else:
										print 'failed to send the mail'
				# query again, regardless of ordering successfully or not
						if flag:
							break
					if flag:
						break
				self.browser.delete_cookie('_jc_save_fromDate')
				if flag:
					break


	def submit_order(self, seat_index):
		print '\n[INFO] found enough tickets, choose passenger and seat'
		try:
			WebDriverWait(self.browser, 8).until(expected_conditions.presence_of_element_located((By.ID, 'normalPassenger_0')))

			# choose passengers
			pers = self.browser.find_element_by_id('normal_passenger_id').find_elements_by_tag_name('label')
			for i in self.passengers:
				pers[i[0]].click()
				if i[1]:
					if i[2]:
						self.browser.find_element_by_id('dialog_xsertcj_ok').click()
					else:
						self.browser.find_element_by_id('dialog_xsertcj_cancel').click()

			# choose seats
			for i in range(len(self.passengers)):
				seats = self.browser.find_element_by_id('seatType_' + str(i+1)).find_elements_by_tag_name('option')
				flag = False
				for seat in seats:
					if self.seat_types[seat_index] in seat.text:
						seat.click()
						flag = True
						break
				if not flag:
					return False

			# submit
			self.browser.find_element_by_id('submitOrder_id').click()
			WebDriverWait(self.browser, 8).until(expected_conditions.visibility_of_element_located((By.ID, 'qr_submit_id')))
			self.browser.find_element_by_id('qr_submit_id').click()
			WebDriverWait(self.browser, 15).until(expected_conditions.presence_of_element_located((By.ID, 'payButton')))

			return True
		except Exception as e:
			print e
			return False
		finally:
			self.browser.save_screenshot('./re.png')

	def send_mail(self, sub, content):  
		msg = MIMEText(content, _subtype='plain', _charset='utf-8')  
		msg['Subject'] = sub
		msg['From'] = self.mail_user
		msg['To'] = ";".join(self.mailto_list)              #将收件人列表以‘;’分隔  
		try:
		    server = smtplib.SMTP()  
		    server.connect(self.mail_host)                       #连接服务器  
		    server.login(self.mail_user, self.mail_pass)               #登录操作  
		    server.sendmail(self.mail_user, self.mailto_list, msg.as_string())
		    server.close()
		    return True
		except Exception, e:
		    print str(e)
		    return False



if __name__ == '__main__':
	try:
		t = Ticket()
		while(t.login()):
			pass
		t.check_ticket()
	finally:
		t.browser.quit()
