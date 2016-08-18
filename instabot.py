#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
import random
import time
import datetime
import json
import signal
import atexit

from random import shuffle
from nested_lookup import nested_lookup


class InstaBot:
    url = 'https://www.instagram.com/'
    url_tag = 'https://www.instagram.com/explore/tags/'
    url_login = 'https://www.instagram.com/accounts/login/ajax/'
    url_logout = 'https://www.instagram.com/accounts/logout/'

    user_agent = ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36")
    accept_language = 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4'

    def __init__(self, login, password):
        self.bot_start = datetime.datetime.now()
        self.time_in_day = 24*60*60

        self.s = requests.Session()

        self.user_login = login.lower()
        self.user_password = password

        now_time = datetime.datetime.now()
        log_string = 'Matrix Activated at %s:\n' %\
                     (now_time.strftime("%d.%m.%Y %H:%M"))
        self.write_log(log_string)
        self.login()

        signal.signal(signal.SIGTERM, self.cleanup)
        atexit.register(self.cleanup)

    def login(self):
        log_string = 'Trying to login as %s...\n' % (self.user_login)
        self.write_log(log_string)
        self.s.cookies.update ({'sessionid' : '', 'mid' : '', 'ig_pr' : '1',
                               'ig_vw' : '1920', 'csrftoken' : '',
                               's_network' : '', 'ds_user_id' : ''})
        self.login_post = {'username' : self.user_login,
                           'password' : self.user_password}
        self.s.headers.update ({'Accept-Encoding' : 'gzip, deflate',
                               'Accept-Language' : self.accept_language,
                               'Connection' : 'keep-alive',
                               'Content-Length' : '0',
                               'Host' : 'www.instagram.com',
                               'Origin' : 'https://www.instagram.com',
                               'Referer' : 'https://www.instagram.com/',
                               'User-Agent' : self.user_agent,
                               'X-Instagram-AJAX' : '1',
                               'X-Requested-With' : 'XMLHttpRequest'})
        r = self.s.get(self.url)
        self.s.headers.update({'X-CSRFToken' : r.cookies['csrftoken']})
        time.sleep(5 * random.random())
        login = self.s.post(self.url_login, data=self.login_post,
                            allow_redirects=True)
        self.s.headers.update({'X-CSRFToken' : login.cookies['csrftoken']})
        self.csrftoken = login.cookies['csrftoken']
        time.sleep(5 * random.random())

        if login.status_code == 200:
            r = self.s.get('https://www.instagram.com/')
            finder = r.text.find(self.user_login)
            if finder != -1:
                self.login_status = True
                log_string = '%s login success!' % (self.user_login)
                self.write_log(log_string)
            else:
                self.login_status = False
                self.write_log('Login error! Check your login data!')
        else:
            self.write_log('Login error! Connection error!')

    def logout(self):
        work_time = datetime.datetime.now() - self.bot_start
        log_string = 'Bot work time: %s' % (work_time)
        self.write_log(log_string)

        try:
            logout_post = {'csrfmiddlewaretoken': self.csrftoken}
            self.s.post(self.url_logout, data=logout_post)
            self.write_log("Logout success!")
            self.login_status = False
        except:
            self.write_log("Logout error!")

    def cleanup(self, *_):
        if (self.login_status):
            self.logout()
        cur_dir = os.path.dirname(__file__)
        for f in os.listdir(os.path.join(cur_dir, "cache")):
            path = os.path.join("cache", f)
            os.unlink(path)
        os.rmdir('cache')
        exit(0)

    def get_media_id_by_tag(self, tag):
        """ Get media ID set, by your hashtag """

        if (self.login_status):
            log_string = "Get media id by tag: %s" % (tag)
            self.write_log(log_string)
            if self.login_status == 1:
                url_tag = '%s%s%s' % (self.url_tag, tag, '/')
                try:
                    r = self.s.get(url_tag)
                    text = r.text

                    finder_text_start = ('<script type="text/javascript">'
                                         'window._sharedData = ')
                    finder_text_start_len = len(finder_text_start)-1
                    finder_text_end = ';</script>'

                    all_data_start = text.find(finder_text_start)
                    all_data_end = text.find(finder_text_end, all_data_start + 1)
                    json_str = text[(all_data_start + finder_text_start_len + 1) \
                                   : all_data_end]
                    all_data = json.loads(json_str)

                    self.media_by_tag = list(all_data['entry_data']['TagPage'][0]\
                                            ['tag']['media']['nodes'])
                except:
                    self.media_by_tag = []
                    self.write_log("Except on get_media!")
                    time.sleep(60)
            else:
                return 0

    def get_images(self):
        r = self.s.get(self.url)
        text = r.text

        finder_text_start = ('<script type="text/javascript">'
                             'window._sharedData = ')
        finder_text_start_len = len(finder_text_start)-1
        finder_text_end = ';</script>'

        all_data_start = text.find(finder_text_start)
        all_data_end = text.find(finder_text_end, all_data_start + 1)
        json_str = text[(all_data_start + finder_text_start_len + 1):all_data_end]
        all_data = json.loads(json_str)
        img_sources = nested_lookup('display_src', all_data)
        shuffle(img_sources)
        #print("total pictures scraped: " + str(len(img_sources)))
        return img_sources

    def save_images(self, urls, starting):
        if not os.path.exists('cache'):
            os.makedirs('cache')
        for url in urls:
            #print('downloading ' + url)
            order_string = 'z'*starting
            res = requests.get(url, stream=True)
            if res.status_code == 200:
                with open('cache/'+order_string+url.split('?')[0].split('/')[-1], 'wb') as f:
                    for chunk in res.iter_content(128):
                        f.write(chunk)
            f.close()
            starting += 1
            #print('done')

    def add_time(self, time):
        """ Make some random for next iteration"""
        return time*0.9 + time*0.2*random.random()

    def write_log(self, log_text):
        return
        try:
            print(log_text)
        except UnicodeEncodeError:
            print("Your text has unicode problem!")
