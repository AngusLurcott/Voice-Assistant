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

# # Dummy JSON list of Events that would be fetched from the DB
FETCHED_EVENTS = [
    {
        "event_name": "Event 1",
        "event_date": "2021-02-25 02:52:15+00:00"
    },
    {
        "event_name": "Doctor's Appointment",
        "event_date": "2021-02-26 14:02:00+00:00"
    },
    {
        "event_name": "Something Else on Calander",
        "event_date": "2021-02-26 17:00:15+00:00"
    },
    {
        "event_name": "A Different thing on Calander",
        "event_date": "2021-02-27 17:00:15+00:00"
    }
]

# FETCHED_EVENTS = [
#     {
#         "event_name": "Goal 1 - Do Something",
#         "event_date": "2021-02-27 10:57:15+00:00"
#     },
#     {
#         "event_name": "Goal 2 - Do Something Else",
#         "event_date": "2021-02-28 14:02:00+00:00"
#     }
# ]

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
        self.db = firebase.initialize_firebase_connection()

        self.schedule_repeating_event(self.sync_remote_events_to_device, datetime.now(),
                                      120, name='calendar')

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
        if msg is not None:

            if 'date' in msg.data:
                date, _ = extract_datetime(msg.data['date'], lang=self.lang)
            else:
                date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)

            reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
            reminder_skill.get_reminders_for_day(reminder_date=serialize(date), reminder_type='calender-event')

    @intent_file_handler('GetNextReminders.intent')
    def get_next_reminder(self, msg=None):
        """ Get the first upcoming reminder. """
        print('Getting next calender event')
        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        reminder_skill.get_next_reminder(reminder_type='calender-event')

    # Adds the fetched JSON List into the reminders list
    def sync_remote_events_to_device(self):
        print('Syncing Events From Firebase')
        user_id = 'NUYwZsdXDWMyVf76FxyLqVsFp043'
        events = self.db.child("events/{}".format(user_id)).get()
        # values = sorted(events, key=lambda k: k['time'], reverse=True)
        for event in events.each():
            if not (self.check_if_reminder_already_on_device(event.key())):
                event_val = event.val()
                dt = parse(event_val.get('time'))
                reminder = event_val.get('name')
                print(f'Check reminder: {reminder}')
                print(f'dt: {dt}')
                if(dt > now_local()):
                    serialized = serialize(dt)
                    print("Adding Reminder", reminder)
                    reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
                    reminder_skill.append_new_reminder(reminder, serialized, 'calender-event', id=event.key())

    def check_if_reminder_already_on_device(self, reminder):
        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
        existing_reminder = [n for n in reminder_skill.get_all_reminders() if n['id'] is not None and n['id'] == reminder]
        return len(existing_reminder) > 0

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
