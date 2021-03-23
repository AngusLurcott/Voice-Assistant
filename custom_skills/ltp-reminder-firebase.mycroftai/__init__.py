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
from mycroft.audio import wait_while_speaking
from mycroft.util import play_wav
from mycroft.messagebus.client import MessageBusClient
import pyrebase
from mycroft.skills import skill_api_method
# Imports HTTPError for if the request made is bad or has an error
from requests import HTTPError

FIREBASE_CONFIG = {
"apiKey": "AIzaSyByc48kOPrTgMOH7y5TLzXbQ3veZ-mlaqw",
"authDomain": "cardiff-smart-speaker-project.firebaseapp.com",
"storageBucket": "cardiff-smart-speaker-project.appspot.com",
"databaseURL": "https://cardiff-smart-speaker-project-default-rtdb.firebaseio.com"
}

REMINDER_PING = join(dirname(__file__), 'twoBeep.wav')

MINUTES = 60  # seconds

DEFAULT_TIME = now_local().replace(hour=8, minute=0, second=0)

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


def is_within_week(d):
    return d.date() <= (datetime.now() + timedelta(7)).date()


def get_day_of_date(d):
    return list(DAY_OF_WEEK.keys())[list(DAY_OF_WEEK.values()).index(d.weekday())]


def contains_datetime(utterance, lang='en-us'):
    return extract_datetime(utterance) is not None


def is_affirmative(utterance, lang='en-us'):
    affirmatives = ['yes', 'sure', 'please do']
    for word in affirmatives:
        if word in utterance:
            return True
    return False


class ReminderSkill(MycroftSkill):
    def __init__(self):
        super(ReminderSkill, self).__init__()
        self.notes = {}
        self.primed = False

        self.cancellable = []  # list of reminders that can be cancelled
        self.NIGHT_HOURS = [23, 0, 1, 2, 3, 4, 5, 6]

    def initialize(self):
        # Handlers for notifications after speak
        # TODO Make this work better in test
        self.initialize_firebase_connection()
        if isinstance(self.bus, MessageBusClient):
            self.bus.on('speak', self.prime)
            # self.bus.on('mycroft.skill.handler.complete', self.notify)
            self.bus.on('mycroft.skill.handler.start', self.reset)

        # Reminder checker event
        self.schedule_repeating_event(self.__check_reminder, datetime.now(),
                                      0.5 * MINUTES, name='reminder')

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

    def __check_reminder(self, message):
        """ Repeating event handler. Checking if a reminder time has been
            reached and presents the reminder. """
        now = now_local()
        handled_reminders = []
        for r in self.settings.get('reminders', []):
            # checks for snoozed reminders, otherwise check date attr
            if('snooze_time' in r):
                dt = deserialize(r['snooze_time'])
            else:
                dt = deserialize(r['date'])

            # check for if it is time to remind the user
            if now > dt:
                play_wav(REMINDER_PING)
                self.speak_dialog('Reminding', data={'reminder': r['name']})
                self.handle_reminder(r)

    def handle_reminder(self, reminder):
        self.log.info(f'Handling Reminder: {reminder}')
        if reminder['type'] == 'calender-event' or reminder['type'] == 'default':
            try:
                self.settings['reminders'].remove(reminder)
            except ValueError:
                pass

            response = self.ask_yesno('Do you want to dismiss this reminder?')
            if response == 'yes':
                # code to cancel reminder
                self.log.info(f'Dismissing Reminder: {reminder}')
                self.cancellable = [c for c in self.cancellable if c != reminder['name']]
                if reminder['type'] == 'calender-event':
                    self.cancel_reminder_in_db(reminder)
            else:
                if ('repeat' in reminder):
                    repeats = reminder['repeat'] + 1
                else:
                    repeats = 0
                # If the reminer hasn't been repeated 3 times reschedule it
                if repeats < 2:
                    self.speak('ok, I will remind you about this in 2 minutes', wait=True)
                    reminder['repeat'] = repeats
                    self.snooze_reminder(reminder)
                    if reminder['name'] not in self.cancellable:
                        self.cancellable.append(reminder['name'])
                else:
                    self.speak('You have reached the maximum number of snoozes', wait=True)
                    self.speak('So I will remove this reminder', wait=True)
                    self.log.info(f'Maximum Snooze reached for reminder: {reminder}')
                    self.cancellable = [c for c in self.cancellable if c != reminder['name']]
                    if reminder['type'] == 'calender-event':
                        self.cancel_reminder_in_db(reminder)

    def snooze_reminder(self, reminder):
        if('snooze_time' in reminder):
            new_time = deserialize(reminder['snooze_time']) + timedelta(minutes=10)
        else:
            new_time = deserialize(reminder['date']) + timedelta(minutes=10)
        self.log.info(f'Reminder Snoozed {reminder}')
        self.log.info(f'with time {serialize(new_time)}')
        if (reminder['type'] == 'calender-event'):

            self.settings['reminders'].append(
                    {'name': reminder['name'],
                    'date': reminder['date'],
                    'type': reminder['type'],
                    'id': reminder['id'],
                    'snooze_time': serialize(new_time),
                    'repeat': reminder['repeat']})
        else:
            self.settings['reminders'].append(
                    {'name': reminder['name'],
                    'date': reminder['date'],
                    'type': reminder['type'],
                    'id': reminder['id'],
                    'snooze_time': serialize(new_time),
                    'repeat': reminder['repeat']})

    def remove_by_name(self, name):
        for r in self.settings.get('reminders', []):
            if r['name'] == name:
                try:
                    self.settings['reminders'].remove(r)
                except ValueError:
                    pass
                return r  # Matching reminder was found and removed
        else:
            return None  # No matching reminders found

    def get_by_name(self, name):
        for r in self.settings.get('reminders', []):
            if r['name'] == name:
                return r
        else:
            return None

    def get_by_id(self, id):
        self.log.info(f'Getting reminder with id: {id}')
        for r in self.settings.get('reminders', []):
            if r['id'] == id:
                return r
        else:
            return None

    def remove_by_id(self, id):
        for r in self.settings.get('reminders', []):
            if r['id'] == id:
                print(f"Removing reminder: {r['name']}")
                try:
                    self.settings['reminders'].remove(r)
                except ValueError:
                    pass
                return True  # Matching reminder was found and removed
        else:
            return False  # No matching reminders found

    def _append_new_reminder(self, reminder):
        if 'reminders' in self.settings:
            print("Adding New Reminder to Existing Reminders List")
            self.settings['reminders'].append(reminder)
            # self.settings['reminders'].append((reminder, serialized))
        else:
            print("Adding New Reminder List")
            self.settings['reminders'] = [reminder]
            # self.settings['reminders'] = [(reminder, serialized)]
        return True

    @skill_api_method
    def update_reminder(self, id, name, serialized_date, reminder_type):
        if(reminder_type == 'calender-event'):
            self.log.info(f'Updating reminder that is Calender-Event')
            reminder = self.get_by_id(id)
            self.log.info(f'Found remidner by id: {reminder}')
            if (reminder):
                dt = deserialize(serialized_date)
                if(dt != deserialize(reminder['date'])):
                    if(dt > now_local()):
                        if('snooze_time' in reminder):
                            self.log.info('Removing snooze on event')
                            del reminder['snooze_time']
                            del reminder['repeat']
                        reminder['date'] = serialized_date
                        self.log.info('Calendar event has a new date')
                    else:
                        self.remove_by_id(reminder['id'])
                        return
                if(reminder['name'] != name):
                    self.log.info('Calendar event has a new name')
                    reminder['name'] = name
                self.remove_by_id(reminder['id'])
                self.log.info(f'Saving updated reminder {reminder}')
                self._append_new_reminder(reminder)
        else:
            dt = deserialize(serialized_date)
            self.remove_by_id(id)
            if (dt > now_local()):
                self.append_new_reminder(name, serialized_date, reminder_type, id)

    def reschedule_by_name(self, name, new_time):
        """ Reschedule the reminder by it's name

            Arguments:
                name:       Name of reminder to reschedule.
                new_time:   New time for the reminder.

            Returns (Bool): True if a reminder was found.
        """
        serialized = serialize(new_time)
        for r in self.settings.get('reminders', []):
            if r['name'] == name:
                break
        else:
            return False  # No matching reminders found
        # Using a more thread-safe way to remove reminders from a list
        # https://stackoverflow.com/a/9915349
        try:
            self.settings['reminders'].remove(r)
        except ValueError:
            pass
        if('repeat' in r):
            repeats = r['repeat'] + 1
        else:
            repeats = 0

        self.settings['reminders'].append({'name': r['name'], 'date': r['date'], 'type': r['type'], 'snooze_time': serialized, 'repeat': repeats})
        return True

    def date_str(self, d):
        if is_today(d):
            return 'today'
        elif is_tomorrow(d):
            return 'tomorrow'
        else:
            return nice_date(d.date())

    @intent_file_handler('ReminderAt.intent')
    @skill_api_method
    def add_new_reminder(self, msg=None):
        """ Handler for adding  a reminder with a name at a specific time. """
        reminder = msg.data.get('reminder', None)
        if reminder is None:
            return self.add_unnamed_reminder_at(msg)

        # mogrify the response TODO: betterify!
        reminder = (' ' + reminder).replace(' my ', ' your ').strip()
        reminder = (' ' + reminder).replace(' our ', ' your ').strip()
        utterance = msg.data['utterance']
        reminder_time, rest = (extract_datetime(utterance, now_local(),
                                                self.lang,
                                                default_time=DEFAULT_TIME) or
                               (None, None))

        if reminder_time:  # A datetime was extracted
            if reminder_time.hour in self.NIGHT_HOURS:
                self.speak_dialog('ItIsNight')
                if not self.ask_yesno('AreYouSure') == 'yes':
                    return  # Don't add if user cancels
            if self.ask_yesno('Do you want to add this to your calender') == 'yes':
                id = self.push_reminder_to_firebase(reminder, reminder_time, 'calender-event')
                self.__save_reminder_local(reminder, reminder_time, 'calender-event', id)
            else:
                self.__save_reminder_local(reminder, reminder_time)
        else:
            self.speak_dialog('NoDateTime')

    def push_reminder_to_firebase(self, reminder, reminder_time, reminder_type):
        login_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        user_id = login_skill.get_user_ID()
        # user_id = 'NUYwZsdXDWMyVf76FxyLqVsFp043'
        if(user_id != ""):
            self.log.info(f'Pushing reminder to db for user: {user_id}')
            if reminder_type == 'calender-event':
                serialized_date_time = reminder_time.strftime('%Y-%m-%dT%H:%M:%S%z')
                date_time = reminder_time.strftime("%Y-%m-%d")
                date = reminder_time.strftime("%Y-%m-%d")
                data = {'name': reminder, 'time': serialized_date_time, 'date': date}
                posted_id = self.db.child("events/{}".format(user_id)).push(data)
                print(f'Reminder saved: {posted_id}')
                return posted_id
        else:
            self.log.info("User is not logged in, couldn't get a User id")

    @skill_api_method
    def update_or_add_reminders(self, reminder_ids, reminders, reminder_type='default'):
        self.remove_redundant_reminders(reminder_ids, 'calender-event')
        for i in range(0, len(reminder_ids)):
            existing_reminder = [n for n in self.get_all_reminders() if n['id'] == reminder_ids[i]]
            existing_reminder = existing_reminder[0] if len(existing_reminder) > 0 else None

            date = reminders[i]['time']
            dt = deserialize(reminders[i]['time'])
            reminder = reminders[i]['name']

            if existing_reminder is not None:
                if(existing_reminder['name'] != reminder or deserialize(existing_reminder['date']) != dt):
                    self.log.info(f'Event needs to be updated {existing_reminder}')
                    self.log.info(f'To new changes {reminders[i]}')
                    self.update_reminder(existing_reminder['id'], reminder, date, existing_reminder['type'])
                else:
                    print('No need to update event')
            #  Adding a new reminder as it doesn't currently exist
            else:
                print(f'Check reminder: {reminder}')
                if(reminder_type == 'calender-event' and 'cancelled' in reminder and (reminder['cancelled'] is True or reminder['cancelled'].lower() == 'true')):
                    continue
                if(dt > now_local()):
                    print("Adding Reminder", reminder)
                    self.append_new_reminder(reminder, date, reminder_type, reminder_ids[i])
                else:
                    print(f'dt was not in the future: {date}')

    def remove_redundant_reminders(self, ids, reminder_type):
        existing_events = [n for n in self.get_all_reminders() if n['type'] == reminder_type]
        for reminder in existing_events:
            if reminder['id'] != 'None' and reminder['id'] not in ids:
                self.remove_by_id(reminder['id'])

    @skill_api_method
    def append_new_reminder(self, reminder, serialized, reminder_type='default', id='None'):
        if 'reminders' in self.settings:
            print("Adding New Reminder to Existing Reminders List")
            self.settings['reminders'].append({'name': reminder, 'date': serialized, 'type': reminder_type, 'id': id})
            # self.settings['reminders'].append((reminder, serialized))
        else:
            print("Adding New Reminder List")
            self.settings['reminders'] = [{'name': reminder, 'date': serialized, 'type': reminder_type, 'id': id}]
            # self.settings['reminders'] = [(reminder, serialized)]
        return True

    def __save_reminder_local(self, reminder, reminder_time, reminder_type='default', id='None'):
        """ Speak verification and store the reminder. """
        # Choose dialog depending on the date
        if is_today(reminder_time):
            self.speak_dialog('SavingReminder',
                              {'timedate': nice_time(reminder_time)})
        elif is_tomorrow(reminder_time):
            self.speak_dialog('SavingReminderTomorrow',
                              {'timedate': nice_time(reminder_time)})
        else:
            self.speak_dialog('SavingReminderDate',
                              {'time': nice_time(reminder_time),
                               'date': nice_date(reminder_time)})

        # Store reminder
        serialized = serialize(reminder_time)
        # Normal reminders are saved as the default type in the list
        self.append_new_reminder(reminder, serialized, reminder_type, id)

    def __save_unspecified_reminder(self, reminder):
        if 'unspec' in self.settings:
            self.settings['unspec'].append(reminder)
        else:
            self.settings['unspec'] = [reminder]

    @intent_file_handler('Reminder.intent')
    def add_unspecified_reminder(self, msg=None):
        """ Starts a dialog to add a reminder when no time was supplied
            for the reminder.
        """
        reminder = msg.data['reminder']
        # Handle the case where padatious misses the time/date
        if contains_datetime(msg.data['utterance']):
            return self.add_new_reminder(msg)

        response = self.get_response('ParticularTime')
        if response and is_affirmative(response):
            # Check if a time was also in the response
            dt, rest = extract_datetime(response) or (None, None)
            # print(f'This is the extra of the dt: {dt} and {rest}')
            if dt is None:
                # No time found in the response
                response = self.get_response('SpecifyTime')
                dt, rest = extract_datetime(response) or None, None
                dt = dt[0]
                # print(f'New DT: {dt} and {rest}')
                if dt is None or response is None:
                    self.speak('Fine, be that way')
                    return

            self.__save_reminder_local(reminder, dt)
        else:
            LOG.debug('put into general reminders')
            self.__save_unspecified_reminder(reminder)

    @intent_file_handler('UnspecifiedReminderAt.intent')
    def add_unnamed_reminder_at(self, msg=None):
        """ Handles the case where a time was given but no reminder
            name was added.
        """
        utterance = msg.data['timedate']
        reminder_time, _ = (extract_datetime(utterance, now_local(), self.lang,
                                             default_time=DEFAULT_TIME) or
                            (None, None))

        response = self.get_response('AboutWhat')
        if response and reminder_time:
            self.__save_reminder_local(response, reminder_time)

    @intent_file_handler('DeleteReminderForDay.intent')
    def remove_reminders_for_day(self, msg=None):
        """ Remove all reminders for the specified date. """
        if 'date' in msg.data:
            date, _ = extract_datetime(msg.data['date'], lang=self.lang)
        else:
            date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)

        date_str = self.date_str(date or now_local().date())
        # If no reminders exists for the provided date return;
        for r in self.settings['reminders']:
            if deserialize(r['date']).date() == date.date():
                break
            if ('snooze_time' in r and deserialize(r['snooze_time']).date() == date.date()):
                break
        else:  # Let user know that no reminders were removed
            self.speak_dialog('NoRemindersForDate', {'date': date_str})
            return

        answer = self.ask_yesno('ConfirmRemoveDay', data={'date': date_str})
        if answer == 'yes':
            if 'reminders' in self.settings:
                self.settings['reminders'] = [
                        r for r in self.settings['reminders']
                        if deserialize(r['date']).date() != date.date() or ('snooze_time' in r and deserialize(r['snooze_time']).date() != date.date())]

    @intent_file_handler('GetRemindersForDay.intent')
    @skill_api_method
    def get_reminders_for_day(self, msg=None, reminder_type=None, reminder_date=None):
        """ List all reminders for the specified date. """
        if msg is not None:
            if 'date' in msg.data:
                date, _ = extract_datetime(msg.data['date'], lang=self.lang)
            else:
                date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)

        if 'reminders' in self.settings:
            if reminder_type is not None and reminder_date is not None:
                reminders = [r for r in self.settings['reminders']
                            if (('snooze_time' in r and deserialize(r['snooze_time']).date() == deserialize(reminder_date).date()) or
                            deserialize(r['date']).date() == deserialize(reminder_date).date()) and r['type'] == reminder_type]
            else:
                reminders = [r for r in self.settings['reminders']
                            if (deserialize(r['date']).date() == date.date() or
                            ('snooze_time' in r and deserialize(r['snooze_time']).date() == date.date()))]

            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt, reminder_type = (r['name'], deserialize(r['date']), r['type'])
                    if('snooze_time' in r):
                        dt = deserialize(r['snooze_time'])
                    # Do things with the reminder type to give a differnt reponse for the reminder

                    # TODO: Needs to say the desired day to get a better idea of the reminder
                    self.speak(reminder + ' at ' + nice_time(dt))
                return
        self.speak_dialog('NoUpcoming')

    @skill_api_method
    def get_all_reminders(self):
        if len(self.settings.get('reminders', [])) > 0:
            return self.settings['reminders']
        else:
            return []

    @intent_file_handler('GetNextReminders.intent')
    @skill_api_method
    def get_next_reminder(self, msg=None, reminder_type=None):
        """ Get the first upcoming reminder. """
        reminders = []
        if len(self.settings.get('reminders', [])) > 0:
            if reminder_type is not None:
                reminders = [r for r in self.settings['reminders']
                            if r['type'] == reminder_type]
            else:
                reminders = [r for r in self.settings['reminders']]

        if (len(reminders) > 0):
            next_reminder = sorted(reminders, key=lambda tup: tup['snooze_time'] if 'snooze_time' in tup else tup['date'])
            if next_reminder:
                next_reminder = next_reminder[0]
                if('snooze_time' in next_reminder):
                    dt = deserialize(next_reminder['snooze_time'])
                else:
                    dt = deserialize(next_reminder['date'])

                if is_today(dt):
                    self.speak_dialog('NextToday',
                                    data={'time': nice_time(dt),
                                            'reminder': next_reminder['name']})
                elif is_tomorrow(dt):
                    self.speak_dialog('NextTomorrow',
                                    data={'time': nice_time(dt),
                                            'reminder': next_reminder['name']})
                elif is_within_week(dt):
                    """ List all reminders for a day in the week. """
                    reminder_day = get_day_of_date(dt)
                    # DAY_OF_WEEK[deserialize(r['date']).weekday()]
                    self.speak_dialog('NextReminderWithinWeek',
                                    data={'time': nice_time(dt),
                                            'date': reminder_day,
                                            'reminder': next_reminder['name']})
                else:
                    self.speak_dialog('NextOtherDate',
                                    data={'time': nice_time(dt),
                                            'date': nice_date(dt),
                                            'reminder': next_reminder['name']})
            else:
                self.speak_dialog('NoUpcoming')
        else:
            self.speak_dialog('NoUpcoming')

    def __cancel_active(self, propagate=False):
        """ Cancel all active reminders. """
        remove_list = []
        ret = len(self.cancellable) > 0  # there were reminders to cancel
        for c in self.cancellable:
            reminder = self.remove_by_name(c)
            if reminder:
                remove_list.append(reminder)
        for c in remove_list:
            self.cancellable.remove(c['name'])
            if propagate:
                self.cancel_reminder_in_db(c)
        return ret

    @intent_file_handler('CancelNextReminder.intent')
    def cancel_next(self, message):
        if len(self.settings.get('reminders', [])) > 0:
            reminders = [r for r in self.settings['reminders']]

            next_reminder = sorted(reminders, key=lambda tup: tup['snooze_time'] if 'snooze_time' in tup else tup['date'])
            next_reminder = next_reminder[0] if next_reminder else None
            if(next_reminder):
                print(f'Next Reminder: {next_reminder}')
                if(next_reminder['id'] != 'None'):
                    self.cancel_reminder_in_db(next_reminder)
                try:
                    self.settings['reminders'].remove(next_reminder)
                except ValueError:
                    pass
                if(next_reminder in self.settings['reminders']):
                    self.speak('Something went wrong')
                else:
                    self.speak('Reminder Cancelled')
            else:
                self.speak('You have no upcoming reminders')
        else:
            self.speak('No Upcoming Reminders to cancel')

    def cancel_reminder_in_db(self, reminder):
        login_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        user_id = login_skill.get_user_ID()
        # TODO: add in routes for the other types of events: goals, essential tasks, etc
        if(user_id != ""):
            self.log.info(f'Cancelling reminder from db for user: {user_id}')
            if reminder['type'] == 'calender-event':
                # serialized_date_time = reminder_time.strftime('%Y-%m-%dT%H:%M:%S%z')
                # date_time = reminder_time.strftime("%Y-%m-%d")
                # date = reminder_time.strftime("%Y-%m-%d")
                # data = {'name': reminder, 'time': serialized_date_time, 'date': date}
                reminder_id = reminder['id']
                del reminder['id']
                reminder['cancelled'] = True
                posted_id = self.db.child("events/{}".format(user_id)).child(reminder_id).update({'cancelled': True})
                print(f'Reminder cancelled: {reminder_id}')
        else:
            self.log.info("User is not logged in, couldn't get a User id")

    @intent_file_handler('CancelActiveReminder.intent')
    def cancel_active(self, message):
        """ Cancel a reminder that's been triggered (and is repeating every
            2 minutes. """
        if self.__cancel_active(propagate=True):
            self.speak_dialog('ReminderCancelled')
        else:
            self.speak_dialog('NoActive')

    @intent_file_handler('SnoozeReminder.intent')
    def snooze_active(self, message):
        """ Snooze the triggered reminders for 15 minutes. """
        remove_list = []
        for c in self.cancellable:
            if self.reschedule_by_name(c,
                                       now_local() + timedelta(minutes=15)):
                self.speak_dialog('RemindingInFifteen')
                remove_list.append(c)
        for c in remove_list:
            self.cancellable.remove(c)

    @intent_file_handler('GetRemindersForThisWeek.intent')
    @skill_api_method
    def get_reminders_for_this_week(self, msg=None, reminder_type=None):
        """ List all reminders for the specified date. """
        nextWeek = datetime.now() + timedelta(7)
        if 'reminders' in self.settings:
            if reminder_type is not None:
                reminders = [r for r in self.settings['reminders']
                            if (deserialize(r['date']).date() <= nextWeek.date() or
                            ('snooze_time' in r and deserialize(r['snooze_time']).date() <= nextWeek.date())) and
                            r['type'] == reminder_type]
            else:
                reminders = [r for r in self.settings['reminders']
                            if deserialize(r['date']).date() <= nextWeek.date() or
                            ('snooze_time' in r and deserialize(r['snooze_time']).date() <= nextWeek.date())]
            reminders = sorted(reminders, key=lambda tup: tup['snooze_time'] if 'snooze_time' in tup else tup['date'])
            temp_day = None
            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt, reminder_type = (r['name'], deserialize(r['date']), r['type'])
                    if('snooze_time' in r):
                        dt = deserialize(r['snooze_time'])
                    # self.speak(reminder + ' at ' + nice_time(dt))
                    if is_today(dt):
                        self.speak_dialog('NextToday',
                                        data={'time': nice_time(dt),
                                                'reminder': r['name']})
                    elif is_tomorrow(dt):
                        self.speak_dialog('NextTomorrow',
                                        data={'time': nice_time(dt),
                                                'reminder': r['name']})
                    elif is_within_week(dt):
                        """ List all reminders for a day in the week. """
                        # reminder_day = DAY_OF_WEEK[deserialize(r['date']).weekday()]
                        reminder_day = get_day_of_date(dt)
                        if (temp_day is None):
                            temp_day = reminder_day
                            self.speak('On ' + temp_day)
                        elif temp_day != reminder_day:
                            temp_day = reminder_day
                            self.speak('On ' + temp_day)
                        else:
                            self.speak('And')

                        # reminder_day = get_day_of_date(deserialize(r['date']))
                        self.speak_dialog('NextReminderWithinWeek_Alternate', data={'time': nice_time(dt), 'reminder': r['name']})
                    else:
                        pass
                return
        self.speak_dialog('NoUpcoming')

    @intent_file_handler('GetRemindersForDayInThisWeek.intent')
    @skill_api_method
    def get_reminders_for_day_in_this_week(self, msg=None, day=None, reminder_type=None):
        """ List all reminders for a day in the week. """
        today = datetime.now().weekday()
        # print("This is the day today,", today);
        if msg is not None:
            captured_day = msg.data['utterance'].split(' ')[-1].upper()
            desired_day = DAY_OF_WEEK[captured_day]
            self.log.info(f'Captured desired day: {desired_day}')
            # print("This is the captured date,", captured_day);
            if(desired_day == today):
                max_date = datetime.now()
            elif(captured_day in DAY_OF_WEEK):
                if (today > desired_day):
                    day_delta = (6 - today) + (desired_day + 1)
                else:
                    day_delta = abs(DAY_OF_WEEK[captured_day] - today)
                max_date = datetime.now() + timedelta(day_delta)
        if day is not None:
            max_date = deserialize(day)
        # print("Looking for this date: ", max_date.date())
        if 'reminders' in self.settings:
            if reminder_type is not None:
                reminders = [r for r in self.settings['reminders']
                            if (deserialize(r['date']).date() == max_date.date() or
                            ('snooze_time' in r and deserialize(r['snooze_time']).date() == date.date())) and r['type'] == reminder_type]
            else:
                reminders = [r for r in self.settings['reminders']
                            if (deserialize(r['date']).date() == max_date.date() or
                            ('snooze_time' in r and deserialize(r['snooze_time']).date() == date.date()))]
            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt, reminder_type = (r['name'], deserialize(r['date']), r['type'])
                    if('snooze_time' in r):
                        dt = deserialize(r['snooze_time'])
                    self.speak(reminder + ' at ' + nice_time(dt) + ' this ' + get_day_of_date(max_date).lower())
                return
        self.speak_dialog('NoUpcoming')

    @intent_file_handler('ClearReminders.intent')
    def clear_all(self, message):
        """ Clear all reminders. """
        if self.ask_yesno('ClearAll') == 'yes':
            self.__cancel_active()
            self.settings['reminders'] = []
            self.speak_dialog('ClearedAll')

    def stop(self, message=None):
        if self.__cancel_active():
            self.speak_dialog('ReminderCancelled')
            return True
        else:
            return False

    def shutdown(self):
        if isinstance(self.bus, MessageBusClient):
            self.bus.remove('speak', self.prime)
            # self.bus.remove('mycroft.skill.handler.complete', self.notify)
            self.bus.remove('mycroft.skill.handler.start', self.reset)


def create_skill():
    return ReminderSkill()