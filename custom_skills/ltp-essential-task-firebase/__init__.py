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
from mycroft.util.format import pronounce_number
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


def deserialize(dt):
    return datetime.strptime(dt, '%Y%d%m-%H%M%S-%z')


def serialize(dt):
    return dt.strftime('%Y%d%m-%H%M%S-%z')


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
    @intent_file_handler('SyncEssentialTasks.intent')
    def sync_remote_tasks_to_device(self):
        self.log.info('Syncing Essential Tasks From Firebase')
        login_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        user_id = login_skill.get_user_ID()
        # user_id = 'PxswL26vdlQQM4AqjwdeMPalNrs1'
        # user_id = 'WiXK5qBcPzLQcLF2h8ishfjAn1p1'
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
        else:
            self.log.info("User is not logged in, couldn't get a User id")

    @intent_file_handler('GetEssentialTasks.intent')
    def get_essential_tasks_for_today(self, msg=None):
        tasks = self.settings.get('essential-tasks', [])
        if(len(tasks) > 0):
            self.speak(f"Here are your essential tasks", wait=True)
            for i in range(0, len(tasks)):
                self.log.info(f'Tasks: {tasks[i]}')
                number = pronounce_number(i + 1, self.lang)
                if(tasks[i]['numPerDay'] == tasks[i]['completed-count']):
                    self.speak(f"the task called {tasks[i]['name']}, has been completed for today", wait=True)
                else:
                    self.speak(f"the task called {tasks[i]['name']}, will need to be completed {tasks[i]['numPerDay']} times today", wait=True)
                    self.speak(f"so far you have done {tasks[i]['completed-count']} out of {tasks[i]['numPerDay']}", wait=True)
        else:
            self.speak(f"You have no essential tasks", wait=True)
            reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
            reminder_skill.remove_redundant_reminders_by_type('essential-tasks')

    def update_or_add_essential_reminders(self, event_contents, type='essential-tasks'):
        self.log.info('--- Checking if essential tasks need to be updated ---')
        for task in event_contents:
            existing_task = [r for r in self.settings.get('essential-tasks', []) if (r['id'] == task['id'])]
            # The goal is already in the device
            if(existing_task):
                existing_task = existing_task[0]
                if(existing_task['name'] != task['name'] or existing_task['type'] != task['type'] or existing_task['numPerDay'] != task['numPerDay']):
                    self.log.info(f'Updating Existing Task Details to: {task}')
                    saved_task = self._update_essential_task(existing_task)
                    # Append to update reminder list
                else:
                    self.log.info(f'No Update required for task: {existing_task}')
            else:  # The goal needs to be added onto the device
                task['completed-count'] = 0
                self.log.info(f'Adding new task into list {task}')
                saved_task = self._append_new_essential_task(task)
                # Append to update reminder list
        self.add_reminders_for_remaining_tasks()

    @skill_api_method
    def add_reminders_for_remaining_tasks(self):
        remaining_tasks = [r for r in self.settings.get('essential-tasks', []) if(r['completed-count'] != r['numPerDay'])]
        remaining_tasks_ids = [r['id'] for r in remaining_tasks]
        self.log.info(f"State of tasks Content: {remaining_tasks}")
        self.log.info(f"State of tasks Ids: {remaining_tasks_ids}")
        # Calls the reminder api to update an existing or add a reminder for any
        # Task that is not yet complete
        if(remaining_tasks):
            self.log.info("Here are the tasks that still need to be completed")
            self.log.info("There are reminders that need to be added for essential tasks")
            reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
            if(reminder_skill):
                reminder_skill.update_or_add_reminders(remaining_tasks_ids, remaining_tasks, 'essential-tasks')

    def _append_new_essential_task(self, task):
        if 'essential-tasks' in self.settings:
            self.log.info("Adding New Task to Existing Essential Task List")
            self.settings['essential-tasks'].append(task)
            # self.settings['reminders'].append((reminder, serialized))
        else:
            self.log.info("Adding New Essential Task List")
            self.settings['essential-tasks'] = [task]
            # self.settings['reminders'] = [(reminder, serialized)]
        return task

    def _update_essential_task(self, task):
        requires_update = False
        if(existing_task['name'] != task['name']):
            self.log.info(f"The name has changed {existing_task['name']} to {task['name']}")
            existing_task['name'] = task['name']
            requires_update = True

        if(existing_task['type'] != task['type']):
            self.log.info(f"the task type has changed {existing_task['type']} to {task['type']}")
            existing_task['type'] = task['type']
            requires_update = True

        if(existing_task['numPerDay'] != task['numPerDay']):
            self.log.info(f"The numPerDay has changed from {existing_task['numPerDay']} to {task['numPerDay']}")
            if(task['numPerDay'] < existing_task['numPerDay'] and existing_task['completed-count'] > task['numPerDay']):
                existing_task['completed-count'] = task['numPerDay']
            existing_task['numPerDay'] = task['numPerDay']
            requires_update = True

        if('hoursBetween' in task):
            if('hoursBetween' in existing_task):
                if(existing_task['hoursBetween'] != task['hoursBetween']):
                    self.log.info(f"The hours between has changed from {existing_task['hoursBetween']} to {task['hoursBetween']}")
                    existing_task['hoursBetween'] = task['hoursBetween']
                    requires_update = True
            else:
                self.log.info('Adding hoursBetween value to task')
                existing_task['hoursBetween'] = task['hoursBetween']
                requires_update = True

        if('hoursBetween' in existing_task and ('hoursBetween' not in task)):
            self.log.info('Removing Hours between from task')
            del existing_task['hoursBetween']
            requires_update = True

        if(requires_update is True):
            self.log.info(f"There was values to update: {existing_task}")
            self.log.info(f"New fetched values update: {task}")
            self.remove_goal_by_id(existing_task['id'])
            self._append_new_essential_task(existing_task)
        else:
            self.log.info(f"There was nothing to update: {existing_task}")
        return existing_task

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
            self.log.info(f"Completing/Incrementing Task {task_name}")
            task = [r for r in self.settings.get('essential-tasks', []) if r['name'].lower() == task_name.lower()]
            if(task):
                task = task[0]
                self.log.info(f"Checking Task: {task}")
                if(task['completed-count'] == task['numPerDay']):
                    self.speak("You have already completed this task for today", wait=True)
                    reminder_skill.remove_by_id_and_type(task['id'], 'essential-tasks')

                elif(task['completed-count'] < task['numPerDay']):
                    self.speak(f"you are {task['completed-count']} of {task['numPerDay']} for {task_name} today", wait=True)
                    response = self.ask_yesno('Can you confirm that you have done this task for now')
                    if response == 'yes':
                        self.log.info('I got a yes from the complete goal question')
                        reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
                        reminder_skill.remove_by_id_and_type(task['id'], 'essential-tasks')
                        self.speak('okay, I will add that you have done the task', wait=True)
                        # self._complete_goal(task)
                        if(task['numPerDay'] - task['completed-count'] == 1):
                            self._complete_goal(task)
                        else:
                            self._increment_goal_complete(task)
                            if('hoursBetween' in task):
                                # TODO: Change back delta was hours=task['hoursBetween']
                                new_time = now_local() + timedelta(hours=task['hoursBetween'])
                            else:
                                # TODO: Change back delta was hours=1
                                new_time = now_local() + timedelta(minutes=90)
                            temp = {'id': task['id'],
                                    'date': serialize(new_time),
                                    'type': 'essential-tasks',
                                    'task-type': task['type'],
                                    'name': task['name'],
                                    'numPerDay': task['numPerDay']}
                            if('hoursBetween' in task):
                                temp['hoursBetween'] = task['hoursBetween']
                            # task['date'] = serialize(new_time)
                            # task['task-type'] = task['type']
                            # task['type'] = 'essential-tasks'

                            reminder_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
                            reminder_skill._append_new_reminder(temp)
                            task['random'] = 'how'
                            time.sleep(1)
                    elif response == 'no':
                        # self._increment_goal_complete(task)
                        self.log.info('I got a no from the complete goal question')
                        self.speak('okay, tell me when you have completed it later', wait=True)

                    else:
                        self.speak(f"sorry I had trouble understanding what you said", wait=True)
                else:
                    self.log.info('Something went wrong when trying to complete a goal')
                self.add_reminders_for_remaining_tasks()
            else:
                self.log.info('The Task does not exist')
                self.speak(f"{task_name} is not a valid task or you have no essential tasks")

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

    @skill_api_method
    def is_goal_complete(self, id, name):
        task = [r for r in self.settings.get('essential-tasks', []) if(r['name'] == name and r['id'] == id)]
        if(task):
            task = task[0]
            return (task['completed-count'] == task['numPerDay'])
        return False

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

    @skill_api_method
    def _increment_goal_complete(self, goal):
        task = [r for r in self.settings.get('essential-tasks', []) if(r['name'] == goal['name'] and r['id'] == goal['id'])]
        if(task):
            task = task[0]
            difference = task['numPerDay'] - task['completed-count']
            if(difference == 0):
                self.log.info('The task is already complete')
                self.speak('This task has already been completed for today', wait=True)
                return True

            elif(difference - 1 == 0):
                self._complete_goal(task)
                return True
            else:
                self.remove_goal_by_id(task['id'])
                task['completed-count'] = task['completed-count'] + 1
                new_difference = task['numPerDay'] - task['completed-count']
                if(new_difference == 1):
                    self.speak('Great, you only have to do this one more time', wait=True)
                else:
                    self.speak(f'Nice, you only have to do this {new_difference} more times', wait=True)
                self._append_new_essential_task(task)
                self.log.info(f'Task has been incremented for today {task}')
                return False
        else:
            self.log.info(f'Something went wrong when completing a essential task, task not in list: task={goal}')
            return True

    @intent_file_handler('ResetEssentialTasks.intent')
    def _reset_task_count_for_day(self):
        tasks = [self.settings.get('essential-tasks', [])]
        if(len(tasks) > 0):
            # tasks = tasks[0]
            # for r in tasks:
            #     self.log.info(f"Checking Task: {r}")
            #     if('completed-count' in r and r['completed-count'] != 0):
            #         self.remove_goal_by_id(r['id'])
            #         self.log.info(f"Resetting Task Counter to 0: {r}")
            #         r['completed-count'] = 0
            #         self._append_new_essential_task(r)
            #     else:
            #         self.log.info(f"Task already at 0: {r}")
            #     task_skill = SkillApi.get('ltp-reminder-firebase.mycroftai')
            #     task_skill.remove_by_id_and_type(r['id'], 'essential-tasks')
            # self.add_reminders_for_remaining_tasks()
            self.settings['essential-tasks'] = []
        else:
            self.log.info(f"There are no essential tasks to reset")
        self.sync_remote_tasks_to_device()

    def remove_goal_by_id(self, id):
        tasks = [self.settings.get('essential-tasks', [])]
        if(len(tasks) > 0):
            tasks = tasks[0]
            for r in tasks:
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
