import feedparser
import re
from bs4 import BeautifulSoup
import requests
import math
import cytoolz
from dateutil import parser

# TODO: Add more RSS Feed urls
# Constant Dict of various RSS Feeds
RSS_FEEDS = {
    'World': 'http://feeds.bbci.co.uk/news/uk/rss.xml',
    'Business': 'http://feeds.bbci.co.uk/news/business/rss.xml',
    # 'Sports': 'http://feeds.bbci.co.uk/sport/rss.xml',
    # 'Travel' : 'http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/england/travel/rss.xml',
    'Entertainment': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml',
    'Science': 'http://feeds.bbci.co.uk/news/science_and_environment/rss.xml?edition=uk',
    'Health': 'http://feeds.bbci.co.uk/news/health/rss.xml?edition=uk'
}

USER_INFORMATION = {}


# function to extract html document from given url
def getHTMLdocument(url):
    # request for HTML document of given url
    response = requests.get(url)
    response.encoding = 'utf-8'
    # response will be provided in JSON format
    return response.content


def get_feed_list():
    keys = list(RSS_FEEDS.keys())
    print("Here are the avaliable Topics:", )
    for i in range(0, len(keys)):
        print(f"{i + 1}. {keys[i]}")
    return keys


def choose_topic():
    keys = get_feed_list()
    while True:
        topic_value_input = int(input("What topic number would you like to get news about? "))
        if(topic_value_input <= len(keys)):
            print("Chosen topic: ", keys[topic_value_input-1])
            break
        else:
            print('Please choose a valid topic number')
    chosen_feed = RSS_FEEDS[keys[topic_value_input-1]]
    print(f"Feed Chosen: {chosen_feed}")
    print("")
    return chosen_feed


def read_article(url):
    print(url)
    html_document = getHTMLdocument(url)

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
            print(paragraph.text)
        if(max_lines == total_lines):
            break
        if(max_lines < total_lines):
            print()
            read_next = input('Do you want to continue? (y/n) ')
            if (read_next == 'y'):
                lines += 4
                print()
                continue
            else:
                print()
                break


def filter_articles_by_published(articles):
    return sorted(articles, key=lambda i: parser.parse(i.published), reverse=True)


def get_articles(topics=[]):
    if len(topics) > 0:
        articles = []
        for topic in topics:
            fp = feedparser.parse(RSS_FEEDS[topic])
            articles += fp.entries[:3]
        # print('list of articles', articles)
        articles = filter_articles_by_published(articles)
    else:
        chosen_feed = choose_topic()
        print("Getting RSS feed from: ", chosen_feed)
        fp = feedparser.parse(chosen_feed)
        # Currently reading the 5th and 6th articles from the rss feed list
        articles = fp.entries[:3]
    articles = list(cytoolz.unique(articles, key=lambda x: x.title))
    for i in range(0, len(articles)):
        print(f"Article {i + 1}")
        print(articles[i].title)
        print(articles[i].published)
        print()
    print()
    for i in range(0, len(articles)):
        print(f"==== Article {i + 1} Information ====")
        print(articles[i].title)
        print(articles[i].summary)
        print(articles[i].link)
        print()
        read = input("Do you want to read this article in more detail? (y/n) ")
        if (read == 'y'):
            print()
            print(f"===== Article {i + 1} Content ====")
            read_article(articles[i].link)
        else:
            print()
            continue


# TODO: Cache results for specific topics and users
def get_news_for_user(user_id=None):
    if(USER_INFORMATION['topics'] is not None):
        pass
    else:
        print('You have not subscribed to any feeds')


# TODO: Add calender events to read new article for topic
def check_new_article(user_id=None):
    pass


# TODO: Add feed to user data
def subscribe_to_feed(topic, user_id=None):
    if(USER_INFORMATION['topics'] is not None):
        print("Here are the topics your are subscribed to: ", USER_INFORMATION['topics'])
    else:
        print('You have not subscribed to any feeds')
    print('---')
    get_feed_list()


# TODO: Remove rss feed from user data
def unsubscribe_from_feed(topic, user_id=None):
    # get_feed_list()
    if(USER_INFORMATION['topics'] is not None):
        print("Here are the topics your are subscribed to: ", USER_INFORMATION['topics'])
    else:
        print('You have not subscribed to any feeds')


def clean_html(raw_html):
    """ Remove html tags from string. """
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    cleantext = html_parser.unescape(cleantext)
    return unicodedata.normalize('NFKD', cleantext).encode('ascii', 'ignore')


# Calling method to start script
get_articles(['World', 'Health'])
