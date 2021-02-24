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
# from mycroft.skills import skill_api_method
# Import the firebase util file for firebase connection
import mycroft.skills.firebase_connection as firebase
# Imports HTTPError for if the request made is bad or has an error
from requests import HTTPError
# Imports parse to parse any JSON dates within the fetched results
from dateutil.parser import parse
import base64

from mycroft.skills.api import SkillApi

# Dummy JSON list of Events that would be fetched from the DB
FETCHED_EVENTS = [
    {
        "event_name": "Event 1",
        "event_date": "2021-02-25 18:00:15+00:00"
    },
    {
        "event_name": "Doctor's Appointment",
        "event_date": "2021-02-26 14:02:00+00:00"
    },
    {
        "event_name": "Something Else on Calander",
        "event_date": "2021-02-26 17:00:15+00:00"
    }
]


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
        self.db = firebase.initialize_firebase_connection()

    def add_notification(self, identifier, note, expiry):
        self.notes[identifier] = (note, expiry)

    def prime(self, message):
        time.sleep(1)
        self.primed = True

    def reset(self, message):
        self.primed = False

    @intent_file_handler('GetRemindersForDay.intent')
    def get_calender_events_for_day(self, msg=None):
        """ List all reminders for the specified date. """
        print("What even is this", msg)
        if 'date' in msg.data:
            date, _ = extract_datetime(msg.data['date'], lang=self.lang)
        else:
            date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)

        reminderSkill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminderSkill.get_reminders_for_day(reminderDate=serialize(date), reminderType='calender-event')

    @intent_file_handler('GetNextReminders.intent')
    def get_next_reminder(self, msg=None):
        """ Get the first upcoming reminder. """
        reminderSkill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminderSkill.get_next_reminder('calender-event')

    # Adds the fetched JSON List into the reminders list
    def sync_remote_events_to_device(self):
        for event in FETCHED_EVENTS:
            # Get reminder name and date from json
            reminder = event.get('event_name')
            dt = parse(event.get('event_date'))
            serialized = serialize(dt)
            print("Adding Reminders", reminder)

            reminderSkill = SkillApi.get('ltp-reminder-firebase.mycroftai')
            reminderSkill.append_new_reminder(reminder, serialized, 'calender-event')

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
        reminderSkill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminderSkill.get_reminders_for_this_week(reminderType='calender-event')

    @intent_file_handler('GetRemindersForDayInThisWeek.intent')
    def get_reminders_for_day_in_this_week(self, msg=None):
        DAY_OF_WEEK = {
            "MONDAY": 0,
            "TUESDAY": 1,
            "WEDNESDAY": 2,
            "THURSDAY": 3,
            "FRIDAY": 4,
            "SATURDAY": 5,
            "SUNDAY": 6
        }
        """ List all reminders for a day in the week. """
        today = datetime.now().weekday()
        # print("This is the day today,", today);
        captured_day = msg.data['utterance'].split(' ')[-1].upper()
        desired_day = DAY_OF_WEEK[captured_day]
        # print("This is the captured date,", captured_day);
        if(desired_day == today):
            maxDate = datetime.now()
        elif(captured_day in DAY_OF_WEEK):
            if (today > desired_day):
                dayDelta = (6 - today) + (desired_day + 1)
            else:
                dayDelta = abs(DAY_OF_WEEK[captured_day] - today)
            maxDate = datetime.now() + timedelta(dayDelta)
        reminderSkill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminderSkill.get_reminders_for_day_in_this_week(day=serialize(maxDate) reminderType='calender-event')

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
