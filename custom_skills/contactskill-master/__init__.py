from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills import MycroftSkill, skill_api_method


#skill api
from mycroft.skills.core import MycroftSkill, intent_handler, skill_api_method
#api skill get skill
from mycroft.skills.api import SkillApi


# imports for pyrebase and parsing JSON Date
from dateutil.parser import parse
import pyrebase
from requests import HTTPError
import base64
# Import Text Magic API
from textmagic.rest import TextmagicRestClient
from itertools import islice
# Import firebase connection
#import mycroft.skills.firebase_connection as firebase
# Email imports
import os
import smtplib
import imghdr
from email.message import EmailMessage


# contents of config file ----------------------------------------------------------------
import pyrebase
import base64
# Firebase Config, API key needs to be changed in production
FIREBASE_CONFIG = {
"apiKey": base64.b64decode("QUl6YVN5QnljNDhrT1ByVGdNT0g3eTVUTHpYYlEzdmVaLW1sYXF3"),
"authDomain": "cardiff-smart-speaker-project.firebaseapp.com",
"storageBucket": "cardiff-smart-speaker-project.appspot.com",
"databaseURL": "https://cardiff-smart-speaker-project-default-rtdb.firebaseio.com"
}

userId = ""


class Contact(MycroftSkill):
    def __init__(self):
        super().__init__()

    def initialize(self):
        # Connecting to firebase
        self.initialize_firebase_connection()

        # Create Text Magic object
        # Text magic username, API Key
        self.client = TextmagicRestClient("anguslurcott", "83e2ltp21gWb6gx1st3WXA4EDeJmSq")

        # Email account details. Currently hardcoded but will change in future
        self.EMAIL_ADDRESS = 'cardiffsmartspeaker@gmail.com'
        self.EMAIL_PASSWORD = 'TM]*N#m}bc<2_sDk'


    # contents of config file ---------------------------------------------------------------------------------------------------
    def initialize_firebase_connection(self):
        firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        auth = firebase.auth()
        self.db = firebase.database()
        #return db


    # Send message method  --- updated -------------------------------------------------------------------------------------------
    @skill_api_method
    def send_message(self, phone_number, sms):
        self.log.info("send text message method called")

        regional_number = str(44) + str(phone_number)
        regional_number = int(regional_number)
        self.log.info(regional_number)
        self.client.messages.create(phones=regional_number, text=sms)
    #--- updated -----------------------------------------------------------------------------------------------------------------


    #Send Email method
    #Parameters are the recipient email address and the email text content
    def send_mail(self, to_email_address, email_text):

        msg = EmailMessage()
        msg['Subject'] = 'Message from a Smart Speaker User'
        msg['From'] = 'cardiffsmartspeaker@gmail.com'
        msg['To'] = to_email_address
        msg.set_content(email_text)

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(self.EMAIL_ADDRESS, self.EMAIL_PASSWORD)
                smtp.send_message(msg)

        except:
            print("Error occured")

    
    # Method to obtain Emergency contact number of user --- updated ----------------------------------------------------------------
    @skill_api_method
    def get_emergency_contact_number(self):

        global userId
        my_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        userId = my_skill.get_user_ID()
        self.log.info(userId)
                    
        try:
            value = self.db.child("contacts/{}".format(userId)).get()
            self.log.info(value)
            for test in value.each():
                if test.val()["emergency"] == "true" or test.val()["emergency"] == "True" or test.val()["emergency"] == True:
                    self.log.info(test.val()["number"])
                    phone_number = test.val()["number"]
                    return phone_number
        except:
            self.speak_dialog("Error, contact not found")
        #--- updated -----------------------------------------------------------------------------------------------------------------


    #Method to obtain emergency contact email of user  --- updated --------------------------------------------------------------------
    @skill_api_method
    def get_emergency_contact_email(self):

        global userId
        my_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        userId = my_skill.get_user_ID()
        self.log.info(userId)
                    
        try:
            value = self.db.child("contacts/{}".format(userId)).get()
            self.log.info(value)
            for test in value.each():
                if test.val()["emergency"] == "true" or test.val()["emergency"] == "True" or test.val()["emergency"] == True:
                    self.log.info(test.val()["email"])
                    email = test.val()["email"]
                    return email
        except:
            self.speak_dialog("Error, contact not found")
        #--- updated -----------------------------------------------------------------------------------------------------------------


    # --- handle sms intent   --- updated --------------------------------------------------------------------------------------------
    @intent_file_handler('smscontact.intent')
    def handle_sms_contact(self, message):
        confirm_response = 'no'
        sms_contact_name = 'default'

        global userId
        my_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        userId = my_skill.get_user_ID()
        self.log.info(userId)

        while confirm_response != 'yes':
            self.speak_dialog('smscontact')
            sms_contact_name = self.get_response().lower()

            self.speak_dialog('Is ' + sms_contact_name + ' the contact you would like to message?')
            confirm_response = self.ask_yesno('')

        sms_message = 'default'
        confirm_message = 'no'

        while confirm_message != 'yes':
            self.speak_dialog("What message would you like to send  " + sms_contact_name)
            sms_message = self.get_response()
            self.speak_dialog('Can you confirm that this is the correct message?')
            self.speak_dialog(sms_message)
            confirm_message = self.ask_yesno('')

        try:

            value = self.db.child("contacts/{}".format(userId)).get()
            self.log.info(value)
            for test in value.each():
                if test.val()["name"] == sms_contact_name:
                    self.log.info(test.val()["number"])
                    phone_number = test.val()["number"]

            self.send_message(phone_number, sms_message)
            self.speak_dialog("Message sent")
        except:
            self.speak_dialog("Error, contact not found")
        #--- updated -----------------------------------------------------------------------------------------------------------------

    # --- handle sms intent   --- updated --------------------------------------------------------------------------------------------
    @intent_file_handler('email.send.intent')
    def handle_email_send(self, message):
        self.speak_dialog('email.send')

        global userId
        my_skill = SkillApi.get('testmotionskillcardiff.c1631548')
        userId = my_skill.get_user_ID()
        self.log.info(userId)

        confirm_response = 'no'

        email_contact_name = 'default'
        while confirm_response!='yes':

            email_contact_name = self.get_response().lower()

            self.speak_dialog('Is ' + email_contact_name + ' the contact you would like to email?')

            confirm_response = self.ask_yesno('')

        email_text = 'default'

        confirm_message = 'no'

        while confirm_message!='yes':

            self.speak_dialog("What would you like to say to  " + email_contact_name)

            email_text = self.get_response()

            self.speak_dialog('Can you confirm that this is the correct message content?')
            self.speak_dialog(email_text)

            confirm_message = self.ask_yesno('')

        try:
            email_address = 'default'

            value = self.db.child("contacts/{}".format(userId)).get()
            self.log.info(value)
            for test in value.each():
                if test.val()["name"] == email_contact_name:
                    self.log.info(test.val()["email"])
                    email_address = test.val()["email"]

            self.send_mail(email_address, email_text)
            self.speak_dialog("Message sent")

        except:
            self.speak_dialog("Error, contact not found")
        #--- updated -----------------------------------------------------------------------------------------------------------------


def create_skill():
    return Contact()
