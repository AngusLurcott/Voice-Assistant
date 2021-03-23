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
from mycroft.messagebus.client import MessageBusClient
# Imports HTTPError for if the request made is bad or has an error
from requests import HTTPError
# Imports parse to parse any JSON dates within the fetched results
from dateutil.parser import parse
import base64
import pyrebase
from mycroft.skills.api import SkillApi
from mycroft.skills import skill_api_method

FIREBASE_CONFIG = {
"apiKey": "AIzaSyByc48kOPrTgMOH7y5TLzXbQ3veZ-mlaqw",
"authDomain": "cardiff-smart-speaker-project.firebaseapp.com",
"storageBucket": "cardiff-smart-speaker-project.appspot.com",
"databaseURL": "https://cardiff-smart-speaker-project-default-rtdb.firebaseio.com"
}


class EssentialTaskFirebaseSkill(MycroftSkill):
    def __init__(self):
        super(EssentialTaskFirebaseSkill, self).__init__()

    def initialize(self):
        # Initialising the Database Connection to Firebase
        self.initialize_firebase_connection()

    def initialize_firebase_connection(self):
        # global userId
        firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        auth = firebase.auth()
        self.db = firebase.database()

    # Adds the fetched JSON List into the reminders list
    @intent_file_handler('GetEssentialTasks.intent')
    def sync_remote_events_to_device(self):
        self.log.info('Syncing Essential Tasks From Firebase')
        # login_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        # user_id = login_skill.get_user_ID()
        user_id = 'PxswL26vdlQQM4AqjwdeMPalNrs1'
        if(user_id != ""):
            self.log.info(f'Getting essential tasks for user: {user_id}')
            events = self.db.child("essential_tasks/{}".format(user_id)).get()

            event_ids, event_contents = [], []
            try:
                for event in events.each():
                    event_val = event.val()
                    self.log.info(f'Here is what I got: {event_val}')
                    if('hoursBetween' in event_val):
                        self.log.info(f"This Task has hours between {event_val.get('hoursBetween')}")
                        # dt = parse(event_val.get('time'))
                        # event_val['time'] = serialize(dt)
                    task_name = event_val.get('name')
                    event_val['id'] = event.key()
                    event_contents.append(event_val)
                    # event_ids.append(event.key())
                # reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
                # reminder_skill.update_or_add_reminders(event_ids, event_contents, 'calender-event')
                self.update_or_add_essential_reminders(event_contents)
            except:
                self.log.info(f'There are no essential tasks for this user {user_id}')
            self.get_events()
        else:
            self.log.info("User is not logged in, couldn't get a User id")

    def get_events(self, msg=None):
        existing_task = [self.log.info(f'Tasks: {r}') for r in self.settings.get('essential-tasks', [])]

    def update_or_add_essential_reminders(self, event_contents, type='essential-tasks'):
        for task in event_contents:
            existing_task = [r for r in self.settings.get('essential-tasks', []) if (r['id'] == task['id'])]
            # The goal is already in the device
            if(existing_task):
                existing_task = existing_task[0]
                if(existing_task['name'] != task['name'] or existing_task['type'] != task['type'] or existing_task['numPerDay'] != task['numPerDay']):
                    self.log.info(f'Updating Existing Task Details to: {task}')
                    self._update_essential_task(existing_task)
                else:
                    self.log.info(f'No Update required for task: {existing_task}')
            else:  # The goal needs to be added onto the device
                task['completed-count'] = 0
                self.log.info(f'Adding new task into list {task}')
                self._append_new_essential_task(task)

    def _append_new_essential_task(self, task):
        if 'essential-tasks' in self.settings:
            self.log.info("Adding New Task to Existing Essential Task List")
            self.settings['essential-tasks'].append(task)
            # self.settings['reminders'].append((reminder, serialized))
        else:
            self.log.info("Adding New Essential Task List")
            self.settings['essential-tasks'] = [task]
            # self.settings['reminders'] = [(reminder, serialized)]
        return True

    def _update_essential_task(self, task):
        if(existing_task['name'] != task['name']):
            existing_task['name'] = task['name']

        if(existing_task['type'] != task['type']):
            existing_task['type'] = task['type']

        if(existing_task['numPerDay'] != task['numPerDay']):
            self.log.info(f"The numPerDay has changed from {existing_task['numPerDay']} to {task['numPerDay']}")
            if(task['numPerDay'] < existing_task['numPerDay']):
                existing_task['completed-count'] = task['numPerDay']
            existing_task['numPerDay'] = task['numPerDay']

        if('hoursBetween' in task):
            if('hoursBetween' in existing_task):
                if(existing_task['hoursBetween'] != task['hoursBetween']):
                    self.log.info(f"The hours between has changed from {existing_task['hoursBetween']} to {task['hoursBetween']}")
                    existing_task['hoursBetween'] = task['hoursBetween']
            else:
                self.log.info('Adding hoursBetween value to task')
                existing_task['hoursBetween'] = task['hoursBetween']

        if('hoursBetween' in existing_task and ('hoursBetween' not in task)):
            self.log.info('Removing Hours between from task')
            del existing_task['hoursBetween']

        self.remove_goal_by_id(existing_task['id'])
        self._append_new_essential_task(existing_task)

    @intent_file_handler('CompleteGoal.intent')
    def completed_goal(self, msg=None, goal_name=None):
        if(msg):
            try:
                task_name = msg.data.get('task_name', None)
            except:
                pass

        if(goal_name):
            task_name = goal_name

        if(task_name):
            task = [r for r in self.settings.get('essential-tasks', []) if r['name'].lower() == task_name.lower()]
            if(task):
                task = task[0]
                self.log.info(f"Checking Task: {task}")
                if(task['completed-count'] == task['numPerDay']):
                    self.speak("You have already completed this task for today", wait=True)

                elif(task['numPerDay'] - task['completed-count'] == 1):
                    self._complete_goal(task)

                elif(task['completed-count'] < task['numPerDay']):
                    self.speak(f"You have done {task['completed-count']} of {task['numPerDay']} for {task_name} today", wait=True)

                    response = self.ask_yesno('Do you want me to complete the task for today')
                    if response == 'yes':
                        self.speak('okay, I will complete the task for today', wait=True)
                        self._complete_goal(task)
                    elif response == 'no':
                        self._increment_goal_complete(task)
                    else:
                        self.speak(f"sorry I had trouble understanding what you said, please start from the beginning", wait=True)
                else:
                    self.log.info('Something went wrong when trying to complete a goal')
            else:
                self.log.info('The Task does not exist')
                self.speak(f"{task_name} is not a valid task")

        else:
            # tasks = self.settings.get('essential-tasks', [])
            self.log.info('I found no task name in utterance')
            remaining_tasks = [r['name'] for r in self.settings.get('essential-tasks', []) if(r['completed-count'] != r['numPerDay'])]

            if(remaining_tasks):
                self.speak('Here are the tasks that you have not completed yet', wait=True)
                response = self.ask_selection(options=[i.lower() for i in remaining_tasks], dialog='Which task are you talking about', numeric=True)
                self.log.info(f"Here is what i got from the task selection: {response}")
                if(response):
                    self.log.info(f'Calling Completed Goal method and passing: {response}')
                    self.completed_goal(goal_name=response)
                    return
                else:
                    self.speak("I had trouble getting the task you said, can you try again", wait=True)
            else:
                self.speak(f"You don't have any tasks to complete for today", wait=True)

    def _complete_goal(self, goal):
        task = [r for r in self.settings.get('essential-tasks', []) if(r['name'] == goal['name'] and r['id'] == goal['id'])]
        if(task):
            task = task[0]
            if(task['completed-count'] == task['numPerDay']):
                self.speak(f"You don't have any more tasks to complete for today", wait=True)
            else:
                task['completed-count'] = task['numPerDay']
                self.remove_goal_by_id(task['id'])
                self.log.info(f'Task has been completed for today {task}')
                self.speak(f"Great this task has been completed for today", wait=True)
                self._append_new_essential_task(task)

        else:
            self.log.info(f'Something went wrong when completing a essential task, task not in list: task={goal}')

    def _increment_goal_complete(self, goal):
        task = [r for r in self.settings.get('essential-tasks', []) if(r['name'] == goal['name'] and r['id'] == goal['id'])]
        if(task):
            task = task[0]
            difference = task['numPerDay'] - task['completed-count']
            if(difference == 0):
                self.log.info('The task is already complete')
                return

            elif(difference - 1 == 0):
                self._complete_goal(goal)
                return
            else:
                task['completed-count'] = task['completed-count'] + 1
                new_difference = task['numPerDay'] - task['completed-count']
                if(new_difference == 1):
                    self.speak('Great, you only have to do this one more time', wait=True)
                else:
                    self.speak(f'Nice, you only have to do this {new_difference} more times', wait=True)
                self.remove_goal_by_id(task['id'])
                self._append_new_essential_task(task)
                self.log.info(f'Task has been incremented for today {task}')
        else:
            self.log.info(f'Something went wrong when completing a essential task, task not in list: task={goal}')

    @intent_file_handler('ResetEssentialTasks.intent')
    def _reset_task_count_for_day(self):
        for r in self.settings.get('essential-tasks', []):
            if('completed-count' in r and r['completed-count'] != 0):
                self.log.info(f"Resetting Task Counter to 0: {r}")
                r['completed-count'] = 0
                self.remove_goal_by_id(r['id'])
                self._append_new_essential_task(r)
            else:
                self.log.info(f"Task already at 0: {r}")

    def remove_goal_by_id(self, id):
        for r in self.settings.get('essential-tasks', []):
            if r['id'] == id:
                self.log.info(f"Removing task: {r['name']}")
                try:
                    self.settings['essential-tasks'].remove(r)
                except ValueError:
                    pass
                return True  # Matching reminder was found and removed
        else:
            return False  # No matching reminders found


def create_skill():
    return EssentialTaskFirebaseSkill()
