from mycroft import MycroftSkill, intent_file_handler
# imports for pyrebase and parsing JSON Date
from dateutil.parser import parse
import pyrebase
from requests import HTTPError
import base64
# Email imports
import os
import smtplib
import imghdr
from email.message import EmailMessage

# Import firebase connection
import mycroft.skills.firebase_connection as firebase
 

class SendEmail(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def initialize(self):

        #Connecting to firebase
        self.db = firebase.initialize_firebase_connection()
        #Setting logged in user as user id 2. This will be updated to reflect the actual logged in user
        self.user_id = 2

        # Email account details. Currently hardcoded but will change in future
        self.EMAIL_ADDRESS = 'cardiffsmartspeaker@gmail.com'
        self.EMAIL_PASSWORD = 'TM]*N#m}bc<2_sDk'

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

    @intent_file_handler('email.send.intent')
    def handle_email_send(self, message):
        self.speak_dialog('email.send')

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
            contacts = self.db.child("contacts/{}".format(self.user_id)).order_by_child("name").equal_to(email_contact_name).get().val()

            values = list(contacts.values())

            email_address = 'default'

            for s in range(len(values)):
                email_address = values[s]['email']

            self.send_mail(email_address, email_text)

            self.speak_dialog("Message sent")

        except:
            self.speak_dialog("Error, contact not found")

def create_skill():
    return SendEmail()

