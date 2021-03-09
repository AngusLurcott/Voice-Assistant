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
import cytoolz

USER_INFORMATION = {'topics': []}

# Constant Dict of various RSS Feeds
RSS_FEEDS = {
    'World': 'http://feeds.bbci.co.uk/news/uk/rss.xml',
    'Business': 'http://feeds.bbci.co.uk/news/business/rss.xml',
    'Entertainment': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml',
    'Science': 'http://feeds.bbci.co.uk/news/science_and_environment/rss.xml?edition=uk',
    'Health': 'http://feeds.bbci.co.uk/news/health/rss.xml?edition=uk'
}


def is_affirmative(utterance, lang='en-us'):
    affirmatives = ['yes', 'sure', 'please do']
    for word in affirmatives:
        if word in utterance:
            return True
    return False


def get_best_matching_title(articles, utterance):
    """ Check the items against the utterance and see which matches best. """
    item_rating_list = []
    for article in articles:
        title = article.title
        # words = get_interesting_words(title)
        words = title.split(' ')
        item_rating_list.append((calc_rating(words, utterance), article))
    return sorted(item_rating_list)[-1]


def calc_rating(words, utterance):
    """ Rate how good a title matches an utterance. """
    rating = 0
    for w in words:
        if w.lower() in utterance.lower():
            rating += 1
    return rating


class RssNewsSkill(MycroftSkill):
    def __init__(self):
        super(RssNewsSkill, self).__init__()

    def initialize(self):
        # Initialising the Database Connection to Firebase
        # self.db = firebase.initialize_firebase_connection()
        pass

    # function to extract html document from given url
    def getHTMLdocument(self, url):
        # request for HTML document of given url
        response = requests.get(url)
        response.encoding = 'utf-8'
        # response will be provided in JSON format
        return response.content

    def get_feed_list(self):
        keys = list(RSS_FEEDS.keys())
        return keys

    def say_feed_list(self):
        keys = self.get_feed_list()
        self.speak("Here are the avaliable Topics:")
        time.sleep(1)
        for i in range(0, len(keys)):
            time.sleep(0.3)
            self.speak(f"{i + 1}. {keys[i]}")
            wait_while_speaking()

    def check_if_topic_is_valid(self, topic):
        return (topic in self.get_feed_list())

    def check_if_user_has_topic(self, topic):
        if USER_INFORMATION['topics'] is not None and len(USER_INFORMATION['topics']) > 0:
            if (topic in USER_INFORMATION['topics']):
                return True
        # self.speak('You currently are not subscribed to any news')
        # wait_while_speaking()
        return False

    def add_topic_into_user_infomation(self, topic):
        if self.check_if_user_has_topic(topic):
            self.speak(f'You are already subscribed to {topic}')
            wait_while_speaking()
        else:
            try:
                if "topics" in USER_INFORMATION:
                    USER_INFORMATION['topics'].append(topic)

                else:
                    USER_INFORMATION['topics'] = [topic]
                self.speak(f"{topic} has been added")
                wait_while_speaking()
            except:
                self.speak("Something went wrong when subscribing")
                wait_while_speaking()

    def remove_topic_from_user_information(self, topic):
        if self.check_if_user_has_topic(topic):
            self.speak(f'Unsubscribing from {topic}')
            wait_while_speaking()
            try:
                if "topics" in USER_INFORMATION:
                    USER_INFORMATION['topics'].remove(topic)
                else:
                    USER_INFORMATION['topics'] = []
            except:
                self.speak("Something went wrong when unsubscribing")
                wait_while_speaking()
        else:
            self.speak(f"You are already not subscribed to this topic")
            wait_while_speaking()

    @intent_file_handler('SubscribeToNewsTopic.intent')
    def subscribe_to_topic(self, msg=None):
        if msg is not None:
            try:
                topic = msg.data['topic']
                if self.check_if_topic_is_valid(topic):
                    self.add_topic_into_user_infomation(topic)
                else:
                    self.speak('The topic you said is not avaliable')
                    wait_while_speaking()
                # add_topic_to_user(topic)
            except:
                self.speak('No topic found')
                print("I didn't find any topic in the utterance so I will ask you now")
                self.choose_topic()
                # add_topic_to_user(topic)

    @intent_file_handler('UnsubscribeFromNewsTopic.intent')
    def unsubscribe_from_topic(self, msg=None):
        if msg is not None:
            try:
                topic = msg.data['topic']
                if self.check_if_topic_is_valid(topic):
                    self.remove_topic_from_user_information(topic)
                else:
                    self.speak('The topic you said is not avaliable')
                    wait_while_speaking()
            except:
                self.speak('No topic found')
                print("I didn't find any topic in the utterance so I will ask you now")
                # TODO: add in logic to show all available user topics

    def choose_topic(self):
        keys = self.say_feed_list()
        repeat = 0
        while True and repeat < 2:
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
            repeat += 1
        chosen_feed = RSS_FEEDS[response]
        print(f"Feed Chosen: {chosen_feed}")
        print("")
        return chosen_feed

    def filter_articles_by_published(self, articles):
        return sorted(articles, key=lambda i: parser.parse(i.published), reverse=True)

    def get_articles(self, topics=[]):
        if len(topics) > 0:
            articles = []
            for topic in topics:
                self.speak(f'Topic: {topic}')
                wait_while_speaking()
                fp = feedparser.parse(RSS_FEEDS[topic])
                articles += fp.entries[:3]
            time.sleep(1)
            # print('list of articles', articles)
            articles = self.filter_articles_by_published(articles)
        else:
            chosen_feed = self.choose_topic()
            self.speak("Getting RSS feed from: ", chosen_feed)
            wait_while_speaking()
            fp = feedparser.parse(chosen_feed)
            # Currently reading the 5th and 6th articles from the rss feed list
            articles = fp.entries[:3]
        articles = list(cytoolz.unique(articles, key=lambda x: x.title))
        return articles

    def speak_articles_list(self, articles):
        for i in range(0, len(articles)):
            self.speak(f"Article {i + 1}")
            wait_while_speaking()
            self.speak(articles[i].title)
            wait_while_speaking()
            self.speak(articles[i].published)
            wait_while_speaking()

    @intent_file_handler('ReadOutUserTopics.intent')
    def read_topics_users_is_subscribed_to(self, msg=None):
        topics = USER_INFORMATION['topics']
        if (len(topics) > 0):
            self.speak('Here are the subscribed topics:')
            for topic in topics:
                self.speak(f'{topic}')
        else:
            self.speak('You are not subscribed to any topics')

    @intent_file_handler('ReadArticleInDetail.intent')
    def read_article_in_detail(self, msg=None):
        # TODO: Get article number or name from feed list
        # Currently need to get the url from the article
        if ('utterance' in msg.data):
            articles = self.get_articles(USER_INFORMATION.get('topics', []))
            self.speak(f'What {len(articles)}')
            best_matched_article = get_best_matching_title(articles, msg.data['utterance'])
            html_document = self.getHTMLdocument(best_matched_article[1].link)

            # create soap object
            soup = BeautifulSoup(html_document, 'html.parser')
            paragraphs = soup.find('article').find_all('div', attrs={'data-component': 'text-block'})
            # Read only 4 lines and then ask for if they want more?
            repeat = math.ceil(len(paragraphs)/4)
            print('Lines', len(paragraphs))
            # print("Repeats", repeat)
            total_lines = len(paragraphs)
        lines = 0

        while lines < total_lines:
            print("Reading from line: ", lines, " of ", total_lines)
            print()
            temp_max = lines + 4
            # Ternary operator to calculate the maximum lines to read in this loop
            max_lines = total_lines if (temp_max > total_lines) else temp_max
            # print("Value of max lines ", max_lines)
            for paragraph in paragraphs[lines:max_lines]:
                self.speak(paragraph.text)
                wait_while_speaking()
            if(max_lines == total_lines):
                break
            if(max_lines < total_lines):
                print()
                response = self.ask_yesno(prompt="Do you want to continue?")
                if (response == 'yes'):
                    lines += 4
                    continue
                else:
                    break

    @intent_file_handler('GiveUserNews.intent')
    def give_user_news(self, msg=None):
        print('Some user information', USER_INFORMATION['topics'])
        if(USER_INFORMATION['topics'] is not None and len(USER_INFORMATION['topics']) > 0):
            articles = self.get_articles(USER_INFORMATION['topics'])
            self.speak_articles_list(articles)
        else:
            self.speak('There are no topics')

    @intent_file_handler('GiveNewsByTopic.intent')
    def give_news_by_topic(self, msg=None):
        if msg is not None:
            try:
                topic = msg.data['topic']
                if self.check_if_topic_is_valid(topic):
                    if self.check_if_user_has_topic(topic):
                        articles = self.get_articles(topics=[topic])
                        self.speak_articles_list(articles)
                    else:
                        print('You are not currently subscribed to this topic')
                        self.speak('Would you like to get updates for this topic?')
                        wait_while_speaking()
                        response = self.get_response()
                        if (response == 'yes'):
                            self.add_topic_into_user_infomation(topic)
                            articles = self.get_articles(topics=[topic])
                            self.speak_articles_list(articles)
                        else:
                            pass
                else:
                    self.speak('The topic you said is not avaliable')
                    wait_while_speaking()
            except Exception as e:
                self.speak('I had a problem trying to get the topic you said, please try again')


def create_skill():
    return RssNewsSkill()
