# Copyright 2016 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from os.path import dirname, join
from datetime import datetime, timedelta
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.parse import extract_datetime, normalize
from mycroft.util.time import now_local
from mycroft.util.format import nice_time, nice_date
from mycroft.util.log import LOG
from mycroft.util import play_wav
from mycroft.audio import wait_while_speaking
from mycroft.messagebus.client import MessageBusClient
# Imports HTTPError for if the request made is bad or has an error
from requests import HTTPError
import base64

# Import the firebase util file for firebase connection
import mycroft.skills.firebase_connection as firebase

# Imports for parsing the RSS feeds and scraping the articles
import feedparser
import re
from bs4 import BeautifulSoup
import requests
import math
from dateutil import parser
import time

USER_INFORMATION = {'topics': []}

# Constant Dict of various RSS Feeds
RSS_FEEDS = {
    'World': 'http://feeds.bbci.co.uk/news/uk/rss.xml',
    'Business': 'http://feeds.bbci.co.uk/news/business/rss.xml',
    'Entertainment': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml',
    'Science': 'http://feeds.bbci.co.uk/news/science_and_environment/rss.xml?edition=uk',
    'Health': 'http://feeds.bbci.co.uk/news/health/rss.xml?edition=uk'
}


class RssNewsSkill(MycroftSkill):
    def __init__(self):
        super(RssNewsSkill, self).__init__()

    def initialize(self):
        # Initialising the Database Connection to Firebase
        # self.db = firebase.initialize_firebase_connection()
        pass

    def get_feed_list(self):
        keys = list(RSS_FEEDS.keys())
        self.speak("Here are the avaliable Topics:")
        time.sleep(1)
        for i in range(0, len(keys)):
            time.sleep(1)
            self.speak(f"{i + 1}. {keys[i]}")
        return keys

    @intent_file_handler('SubscribeToNewsTopic.intent')
    def subscribe_to_topic(self, msg=None):
        if msg is not None:
            try:
                topic = msg.data['topic']
                self.speak(topic)
                # add_topic_to_user(topic)
            except:
                self.speak('No topic found')
                print("I didn't find any topic in the utterance so I will ask you now")
                self.choose_topic()
                # add_topic_to_user(topic)

    def choose_topic(self):
        keys = self.get_feed_list()
        while True:
            time.sleep(5)
            self.speak('Tell me the topic you want news about')
            wait_while_speaking()
            response = self.get_response()
            try:
                response = response.lower().capitalize()
                if (response in keys):
                    self.speak(f"{response} added.")
                    break
                else:
                    self.speak(f"{response} is not in the avaliable choices")
            except:
                self.speak("Something went wrong")
        chosen_feed = RSS_FEEDS[response]
        print(f"Feed Chosen: {chosen_feed}")
        print("")
        return chosen_feed

    @intent_file_handler('UnsubscribeToNewsTopic.intent')
    def unsubscribe_from_topic(self, msg=None):
        pass


def create_skill():
    return RssNewsSkill()
