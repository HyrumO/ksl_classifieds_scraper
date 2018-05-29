"""Scrape KSL for user's searches and send notification with results."""

from datetime import datetime as dt
from datetime import timedelta as td
from email.mime.text import MIMEText
import json
# import pickle
from pprint import pformat
import re
import smtplib
from time import sleep
from urllib import parse

from bs4 import BeautifulSoup as bsoup
import requests as r


with open('config.json') as config_file:
    config = json.load(config_file)

now = dt.now()
yesterday = now - td(hours=24)

# try:
#     with open('results.pickle', 'rb') as p:
#         results = pickle.load(p)
# except FileNotFoundError:
#     results = {}

try:
    urls = [u.strip() for u in open('urls.txt').readlines() if u != '']
except FileNotFoundError:
    print('ERR: you must create a file called "urls.txt" by copying and '
          'pasting the urls from the search results page.\n\n'
          'For example: https://www.ksl.com/classifieds/search/?keyword=iphone&zip=84602&miles=25&priceFrom=&priceTo=&marketType%5B%5D=Sale&city=&state=&sort=0\n\n'
          'You will receive one email for each url.')
    exit()

headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36'}

session = r.Session()
for url in urls:
    out_dict = {}
    print(f'fetching {url}...')
    next_url = url
    while next_url:
        sleep(2)
        source = session.get(next_url, headers=headers).text
        soup = bsoup(source, 'html5lib')
        results_json = re.search(r'window.renderSearchSection\((.*?)\)</script>', source, re.S).group(1)
        results_json = re.sub(r'^\{\s*listings', '{"listings"', results_json)
        results_json = re.sub(r'\s*spotlights: \[', '"spotlights": [', results_json)
        results_json = re.sub(r'\s*displayType: \'', '"displayType": \'', results_json)
        results_json = re.sub(r':\s*\'grid\'', ': "grid"', results_json)
        results_json = re.sub(r'\s*userData:\s*\{', '"userData": {', results_json)
        results_json = re.sub(r'\s*gptAdZones:\s*\[', '"gptAdZones": [', results_json)
        print('results_json:', results_json)
        results = json.loads(results_json)
        print('results:', results)
        for result in results['listings']:
            modtime = result['modifyTime'].replace(':', '').replace('-', '')
            modtime = dt.strptime(modtime, '%Y%m%dT%H%M%SZ')
            if yesterday <= modtime <= now:
                result_id = result['id']
                result_txt = pformat(result)
                out_dict[result_id] = result_txt

        next_link = soup.find('a', class_='next')
        print('    link', next_link)
        try:
            next_url = 'https://www.ksl.com' + next_link.get('href')
        except AttributeError:
            next_url = None
        print('    next_url', next_url)

    print(f'Done with {url}')
    if len(out_dict) > 0:
        print('Building email message...')
        b = '\n\n' + '=' * 79 + '\n'
        m = b.join([f'https://ksl.com/classifieds/listing/{res_id}\n\n{res}' for res_id, res in out_dict.items()])
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
    else:
        print('No new listings.')
