"""Scrape KSL for user's searches and send notification with results."""

from email.mime.text import MIMEText
import json
import os
import pickle
from pprint import pformat
import smtplib
from time import sleep
from urllib import parse

from bs4 import BeautifulSoup as bsoup
import requests as r


with open('config.json') as config_file:
    config = json.load(config_file)


# class WebDriver:
#     def __init__(self, driver):
#         try:
#             with open('results.pickle', 'rb') as p:
#                 driver.results = pickle.load(p)
#         except FileNotFoundError:
#             driver.results = {}
#         self.driver = driver
# 
#     def __enter__(self):
#         return self.driver
# 
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         with open('results.pickle', 'wb') as p:
#             pickle.dump(self.driver.results, p)
#         self.driver.quit()

try:
    urls = [u.strip() for u in open('urls.txt').readlines() if u != '']
except FileNotFoundError:
    print('ERR: you must create a file called "urls.txt" by copying and '
          'pasting the urls from the search results page.\n\n'
          'For example: https://www.ksl.com/classifieds/search/?keyword=iphone&zip=84602&miles=25&priceFrom=&priceTo=&marketType%5B%5D=Sale&city=&state=&sort=0\n\n'
          'You will receive one email for each url.')
    exit()

# with WebDriver(webdriver.Chrome()) as driver:
for url in urls:
    results = {}
    print(f'fetching {url}...')
    next_url = url
    while next_url:
        source = r.get(next_url).text
        soup = bsoup(source, 'html5lib')
        for result in soup.find_all(class_='listing-item'):
            result_id = result.find(name='listing-item-link').get('href')
            result_txt = result.find(name='listing-item-info').get_text()
            results[f'https://ksl.com{result_id}'] = result_txt

        next_link = soup.find(class_='next')
        print('    link', next_link)
        try:
            next_url = next_link.get('href')
        except AttributeError:
            next_url = None
        print('    next_url', next_url)

    print(f'Done with {url}')
    print('Building email message...')
    b = '\n\n' + '=' * 79 + '\n'
    m = b.join([f'{res_id}\n\n{res}' for res_id, res in results.items()])
    msg = MIMEText(m)
    keyword = parse.parse_qs(parse.urlparse(url).query)['keyword'][0]
    msg['Subject'] = f'[KSL] {keyword}'
    msg['From'] = config['from']
    msg['To'] = config['to']

    print('Connecting to SMTP server...')
    with smtplib.SMTP_SSL(config['server']) as s:
    # s = smtplib.SMTP(config['server'], config['port'])
        print('    Logging in...')
        s.login(config['user'], config['drowssap'])
        print('    Sending message...')
        s.send_message(msg)
        print('    Message sent!')
