from mycroft import MycroftSkill, intent_file_handler
# imports for pyrebase and parsing JSON Date
from dateutil.parser import parse
import pyrebase
from requests import HTTPError
import base64
# Import Text Magic API
from textmagic.rest import TextmagicRestClient
from itertools import islice

# Import firebase connection
import mycroft.skills.firebase_connection as firebase
 

class Smscontact(MycroftSkill):




    def __init__(self):

        super().__init__()
    def initialize(self):

        #Connecting to firebase
        self.db = firebase.initialize_firebase_connection()
        #Setting logged in user as user id 2. This will be updated to reflect the actual logged in user
        self.user_id = 2

        # Create Text Magic object
        # Text magic username, API Key
        self.client = TextmagicRestClient("anguslurcott","83e2ltp21gWb6gx1st3WXA4EDeJmSq")



    # Send message method
    #
    def sendMessage(self, phone_number, sms):

        self.client.messages.create(phones=phone_number, text = sms)
        

    @intent_file_handler('smscontact.intent')
    def handle_smscontact(self, message):



        confirm_response = 'no'

        sms_contact_name = 'default'
        while confirm_response!='yes':

            self.speak_dialog('smscontact')
            sms_contact_name = self.get_response().lower()


            self.speak_dialog('Is ' + sms_contact_name + ' the contact you would like to message?')

            confirm_response = self.ask_yesno('')


        sms_message = 'default'

        confirm_message = 'no'

        while confirm_message!='yes':

            self.speak_dialog("What message would you like to send  " + sms_contact_name)

            sms_message = self.get_response()

            self.speak_dialog('Can you confirm that this is the correct message?')
            self.speak_dialog(sms_message)

            confirm_message = self.ask_yesno('')





        
        try:
            contacts = self.db.child("contacts/{}".format(self.user_id)).order_by_child("name").equal_to(sms_contact_name).get().val()

   


            values = list(contacts.values())

            phone_number = 0

            for s in range(len(values)):
                phone_number = values[s]['number']


            self.sendMessage(phone_number, sms_message)

            self.speak_dialog("Message sent")
        

        except:
            self.speak_dialog("Error, contact not found")


      

def create_skill():
    return Smscontact()

