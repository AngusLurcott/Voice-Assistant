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
from mycroft.messagebus.client import MessageBusClient
from mycroft.skills import skill_api_method
# Imports HTTPError for if the request made is bad or has an error
from requests import HTTPError
# Imports parse to parse any JSON dates within the fetched results
from dateutil.parser import parse
import base64
import pyrebase
from mycroft.skills.api import SkillApi

FIREBASE_CONFIG = {
"apiKey": "AIzaSyByc48kOPrTgMOH7y5TLzXbQ3veZ-mlaqw",
"authDomain": "cardiff-smart-speaker-project.firebaseapp.com",
"storageBucket": "cardiff-smart-speaker-project.appspot.com",
"databaseURL": "https://cardiff-smart-speaker-project-default-rtdb.firebaseio.com"
}

DAY_OF_WEEK = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6
}


def deserialize(dt):
    return datetime.strptime(dt, '%Y%d%m-%H%M%S-%z')


def serialize(dt):
    return dt.strftime('%Y%d%m-%H%M%S-%z')


def is_today(d):
    return d.date() == now_local().date()


def is_tomorrow(d):
    return d.date() == now_local().date() + timedelta(days=1)


def contains_datetime(utterance, lang='en-us'):
    return extract_datetime(utterance) is not None


def is_affirmative(utterance, lang='en-us'):
    affirmatives = ['yes', 'sure', 'please do']
    for word in affirmatives:
        if word in utterance:
            return True
    return False


class CalanderEventFirebaseSkill(MycroftSkill):
    def __init__(self):
        super(CalanderEventFirebaseSkill, self).__init__()

    def initialize(self):
        # Initialising the Database Connection to Firebase
        self.initialize_firebase_connection()

        self.schedule_repeating_event(self.sync_remote_events_to_device, datetime.now(),
                                      120, name='calendar')

    def initialize_firebase_connection(self):
        # global userId
        firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        auth = firebase.auth()
        self.db = firebase.database()
        # self.login()

    def add_notification(self, identifier, note, expiry):
        self.notes[identifier] = (note, expiry)

    def prime(self, message):
        time.sleep(1)
        self.primed = True

    def reset(self, message):
        self.primed = False

    '''If the skill api method is used, make sure to use
    SimpleNamespace to create an object as the msg
    from types import SimpleNamespace
    sn = SimpleNamespace(data={'date':'today'})
    arg takes in an object that requires a msg.data attr'''
    @skill_api_method
    @intent_file_handler('GetRemindersForDay.intent')
    def get_calender_events_for_day(self, msg=None):
        """ List all reminders for the specified date. """
        if msg is not None:

            if 'date' in msg.data:
                date, _ = extract_datetime(msg.data['date'], lang=self.lang)
            else:
                date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)

            reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
            reminder_skill.get_reminders_for_day(reminder_date=serialize(date), reminder_type='calender-event')

    @skill_api_method
    def get_calender_events_for_today():
        today = now_local()
        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminder_skill.get_reminders_for_day(reminder_date=serialize(today), reminder_type='calender-event')

    @intent_file_handler('GetNextReminders.intent')
    def get_next_reminder(self, msg=None):
        """ Get the first upcoming reminder. """
        print('Getting next calender event')
        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminder_skill.get_next_reminder(reminder_type='calender-event')

    # Adds the fetched JSON List into the reminders list
    def sync_remote_events_to_device(self):
        print('Syncing Events From Firebase')
        login_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        user_id = login_skill.get_user_ID()
        # user_id = 'NUYwZsdXDWMyVf76FxyLqVsFp043'
        if(user_id != ""):
            self.log.info(f'Getting calender events for user: {user_id}')
            events = self.db.child("events/{}".format(user_id)).get()

            event_ids, event_contents = [], []
            try:
                for event in events.each():
                    event_val = event.val()
                    if('cancelled' in event_val and (event_val['cancelled'] is True)):
                        print('Cancelled Reminder so not adding')
                        continue
                    if('time' in event_val):
                        dt = parse(event_val.get('time'))
                        event_val['time'] = serialize(dt)
                    reminder = event_val.get('name')
                    event_contents.append(event_val)
                    event_ids.append(event.key())
                reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
                reminder_skill.update_or_add_reminders(event_ids, event_contents, 'calender-event')
            except:
                self.log.info(f'There are no user events for this user {user_id}')
        else:
            self.log.info("User is not logged in, couldn't get a User id")

    # Intent to connect to firebase and update the system reminder list
    @intent_file_handler('ConnectToFirebase.intent')
    def handle_connection_firebase(self, message):
        try:
            # Currently checks values inside the users table
            # TODO: Use the Events/Reminders table
            users = self.db.child("users").get()
            self.speak_dialog('FirebaseFetchResult', {'data': f"for the users table, {len(users.val())} records found"})
            self.sync_remote_events_to_device()
        except HTTPError as e:
            if e.response.status_code == 401:
                LOG.error('Could not refresh token, invalid refresh code.')
            else:
                raise

    @intent_file_handler('GetRemindersForThisWeek.intent')
    def get_reminders_for_this_week(self, msg=None):
        """ List all reminders for the specified date. """
        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminder_skill.get_reminders_for_this_week(reminder_type='calender-event')

    @intent_file_handler('GetRemindersForDayInThisWeek.intent')
    def get_reminders_for_day_in_this_week(self, msg=None):
        """ List all reminders for a day in the week. """
        today = now_local().weekday()
        # print("This is the day today,", today);
        captured_day = msg.data['utterance'].split(' ')[-1].upper()
        desired_day = DAY_OF_WEEK[captured_day]
        # print("This is the captured date,", captured_day);
        if(desired_day == today):
            max_date = now_local()
        elif(captured_day in DAY_OF_WEEK):
            if (today > desired_day):
                day_delta = (6 - today) + (desired_day + 1)
            else:
                day_delta = abs(DAY_OF_WEEK[captured_day] - today)
            max_date = now_local() + timedelta(day_delta)
        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminder_skill.get_reminders_for_day_in_this_week(day=serialize(max_date), reminder_type='calender-event')

    # To here
    # @intent_file_handler('ClearReminders.intent')
    # def clear_all(self, message):
    #     """ Clear all reminders. """
    #     if self.ask_yesno('ClearAll') == 'yes':
    #         self.__cancel_active()
    #         self.settings['reminders'] = []
    #         self.speak_dialog('ClearedAll')


def create_skill():
    return CalanderEventFirebaseSkill()
