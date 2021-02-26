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
        if isinstance(self.bus, MessageBusClient):
            self.bus.on('speak', self.prime)
            # self.bus.on('mycroft.skill.handler.complete', self.notify)
            self.bus.on('mycroft.skill.handler.start', self.reset)

        # Reminder checker event
        self.schedule_repeating_event(self.__check_reminder, datetime.now(),
                                      0.5 * MINUTES, name='reminder')

    def add_notification(self, identifier, note, expiry):
        self.notes[identifier] = (note, expiry)

    def prime(self, message):
        time.sleep(1)
        self.primed = True

    def reset(self, message):
        self.primed = False

    # def notify(self, message):
    #     time.sleep(10)
    #     if self.name in message.data.get('name', ''):
    #         self.primed = False
    #         return

    #     handled_reminders = []
    #     now = now_local()
    #     if self.primed:
    #         for r in self.settings.get('reminders', []):
    #             print('Checking {}'.format(r))
    #             dt = deserialize(r['date'])
    #             if now > dt - timedelta(minutes=10) and now < dt and \
    #                     r['name'] not in self.cancellable:
    #                 handled_reminders.append(r)
    #                 self.speak_dialog('ByTheWay', data={'reminder': r['name']})
    #                 self.cancellable.append(r['name'])

    #         self.primed = False

    def __check_reminder(self, message):
        """ Repeating event handler. Checking if a reminder time has been
            reached and presents the reminder. """
        now = now_local()
        handled_reminders = []
        for r in self.settings.get('reminders', []):
            dt = deserialize(r['date'])
            if now > dt:
                play_wav(REMINDER_PING)
                self.speak_dialog('Reminding', data={'reminder': r['name']})
                handled_reminders.append(r)
            if now > dt - timedelta(minutes=10):
                self.add_notification(r['name'], r['name'], dt)
        self.remove_handled(handled_reminders)

    def remove_handled(self, handled_reminders):
        """ The reminder is removed and rescheduled to repeat in 2 minutes.

            It is also marked as "cancellable" allowing "cancel current
            reminder" to remove it.

            Repeats a maximum of 3 times.
        """
        for r in handled_reminders:
            if ('repeat' in r):
                repeats = r['repeat'] + 1
            else:
                repeats = 1
            self.settings['reminders'].remove(r)
            # If the reminer hasn't been repeated 3 times reschedule it
            if repeats < 2:
                self.speak_dialog('ToCancelInstructions')
                new_time = deserialize(r['date']) + timedelta(minutes=2)
                self.settings['reminders'].append(
                    {'name': r['name'],
                    'date': serialize(new_time),
                    'type': r['type'],
                    'repeat': repeats})

                # Make the reminder cancellable
                if r['name'] not in self.cancellable:
                    self.cancellable.append(r['name'])
            else:
                # Do not schedule a repeat and remove the reminder from
                # the list of cancellable reminders
                self.cancellable = [c for c in self.cancellable if c != r['name']]

    def remove_by_name(self, name):
        for r in self.settings.get('reminders', []):
            if r['name'] == name:
                break
        else:
            return False  # No matching reminders found
        self.settings['reminders'].remove(r)
        return True  # Matching reminder was found and removed

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
        self.settings['reminders'].remove(r)
        self.settings['reminders'].append({'name': r['name'], 'date': serialized, 'type': r['type']})
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

        if reminder_time.hour in self.NIGHT_HOURS:
            self.speak_dialog('ItIsNight')
            if not self.ask_yesno('AreYouSure') == 'yes':
                return  # Don't add if user cancels

        if reminder_time:  # A datetime was extracted
            self.__save_reminder_local(reminder, reminder_time)
        else:
            self.speak_dialog('NoDateTime')

    @skill_api_method
    def append_new_reminder(self, reminder, serialized, reminderType='default'):
        if 'reminders' in self.settings:
            print("Adding New Reminder to Existing Reminders List")
            self.settings['reminders'].append({'name': reminder, 'date': serialized, 'type': reminderType})
            # self.settings['reminders'].append((reminder, serialized))
        else:
            print("Adding New Reminder List")
            self.settings['reminders'] = [{'name': reminder, 'date': serialized, 'type': reminderType}]
            # self.settings['reminders'] = [(reminder, serialized)]
        return True

    def __save_reminder_local(self, reminder, reminder_time):
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
        self.append_new_reminder(reminder, serialized, 'default')

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
            if dt:
                # No time found in the response
                response = self.get_response('SpecifyTime')
                dt, rest = extract_datetime(response) or None, None
                if dt:
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
        else:  # Let user know that no reminders were removed
            self.speak_dialog('NoRemindersForDate', {'date': date_str})
            return

        answer = self.ask_yesno('ConfirmRemoveDay', data={'date': date_str})
        if answer == 'yes':
            if 'reminders' in self.settings:
                self.settings['reminders'] = [
                        r for r in self.settings['reminders']
                        if deserialize(r['date']).date() != date.date()]

    @intent_file_handler('GetRemindersForDay.intent')
    @skill_api_method
    def get_reminders_for_day(self, msg=None, reminderType=None, reminderDate=None):
        """ List all reminders for the specified date. """
        if msg is not None:
            if 'date' in msg.data:
                date, _ = extract_datetime(msg.data['date'], lang=self.lang)
            else:
                date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)

        if 'reminders' in self.settings:
            if reminderType is not None and reminderDate is not None:
                reminders = [r for r in self.settings['reminders']
                            if (deserialize(r['date']).date() == deserialize(reminderDate).date()) & (r['type'] == reminderType)]
            else:
                reminders = [r for r in self.settings['reminders']
                            if deserialize(r['date']).date() == date.date()]

            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt, reminderType = (r['name'], deserialize(r['date']), r['type'])
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
    def get_next_reminder(self, msg=None, reminderType=None):
        """ Get the first upcoming reminder. """
        if len(self.settings.get('reminders', [])) > 0:
            if reminderType is not None:
                reminders = [r for r in self.settings['reminders']
                            if r['type'] == reminderType]
            else:
                # reminders = [r for r in self.settings['reminders']
                #             if deserialize(r['date']).date() == date.date()]
                reminders = [r for r in self.settings['reminders']]

        if (len(reminders) > 0):
            next_reminder = sorted(reminders, key=lambda tup: tup['date'])[0]
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
                reminderDay = get_day_of_date(dt)
                # DAY_OF_WEEK[deserialize(r['date']).weekday()]
                self.speak_dialog('NextReminderWithinWeek',
                                data={'time': nice_time(dt),
                                        'date': reminderDay,
                                        'reminder': next_reminder['name']})
            else:
                self.speak_dialog('NextOtherDate',
                                data={'time': nice_time(dt),
                                        'date': nice_date(dt),
                                        'reminder': next_reminder['name']})
        else:
            self.speak_dialog('NoUpcoming')

    def __cancel_active(self):
        """ Cancel all active reminders. """
        remove_list = []
        ret = len(self.cancellable) > 0  # there were reminders to cancel
        for c in self.cancellable:
            if self.remove_by_name(c):
                remove_list.append(c)
        for c in remove_list:
            self.cancellable.remove(c)
        return ret

    @intent_file_handler('CancelActiveReminder.intent')
    def cancel_active(self, message):
        """ Cancel a reminder that's been triggered (and is repeating every
            2 minutes. """
        if self.__cancel_active():
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
    def get_reminders_for_this_week(self, msg=None, reminderType=None):
        """ List all reminders for the specified date. """
        nextWeek = datetime.now() + timedelta(7)
        if 'reminders' in self.settings:
            if reminderType is not None:
                reminders = [r for r in self.settings['reminders']
                            if deserialize(r['date']).date() <= nextWeek.date() and r['type'] == reminderType]
            else:
                reminders = [r for r in self.settings['reminders']
                            if deserialize(r['date']).date() <= nextWeek.date()]
            reminders = sorted(reminders, key=lambda tup: tup['date'])
            tempDay = None
            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt, reminderType = (r['name'], deserialize(r['date']), r['type'])
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
                        # reminderDay = DAY_OF_WEEK[deserialize(r['date']).weekday()]
                        reminderDay = get_day_of_date(dt)
                        if (tempDay is None):
                            tempDay = reminderDay
                            self.speak('On ' + tempDay)
                        elif tempDay != reminderDay:
                            tempDay = reminderDay
                            self.speak('On ' + tempDay)
                        else:
                            self.speak('And')

                        # reminderDay = get_day_of_date(deserialize(r['date']))
                        self.speak_dialog('NextReminderWithinWeek_Alternate', data={'time': nice_time(dt), 'reminder': r['name']})
                    else:
                        pass
                return
        self.speak_dialog('NoUpcoming')

    @intent_file_handler('GetRemindersForDayInThisWeek.intent')
    @skill_api_method
    def get_reminders_for_day_in_this_week(self, msg=None, day=None, reminderType=None):
        """ List all reminders for a day in the week. """
        today = datetime.now().weekday()
        # print("This is the day today,", today);
        if msg is not None:
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
        if day is not None:
            maxDate = deserialize(day)
        # print("Looking for this date: ", maxDate.date())
        if 'reminders' in self.settings:
            if reminderType is not None:
                reminders = [r for r in self.settings['reminders']
                            if deserialize(r['date']).date() == maxDate.date() and r['type'] == reminderType]
            else:
                reminders = [r for r in self.settings['reminders']
                            if deserialize(r['date']).date() == maxDate.date()]
            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt, reminderType = (r['name'], deserialize(r['date']), r['type'])
                    self.speak(reminder + ' at ' + nice_time(dt) + ' this ' + get_day_of_date(maxDate))
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
