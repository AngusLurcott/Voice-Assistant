# Ensure pyrebase is installed inside of the mycroft virtual environment
import pyrebase
import base64

# Firebase Config, API key needs to be changed in production
FIREBASE_CONFIG = {
"apiKey": base64.b64decode("QUl6YVN5QnljNDhrT1ByVGdNT0g3eTVUTHpYYlEzdmVaLW1sYXF3"),
"authDomain": "cardiff-smart-speaker-project.firebaseapp.com",
"storageBucket": "cardiff-smart-speaker-project.appspot.com",
"databaseURL": "https://cardiff-smart-speaker-project-default-rtdb.firebaseio.com"
}

''' 
Import this file into your skills using import mycroft.skills.firebase_connection as {}
Then you are able to call this connection method within your skill and returns the database
See snippet for more help on how to use for your skill:
https://git.cardiff.ac.uk/c1888425/cardiff-smart-speaker-voice-app/-/snippets/53


Feel free to make changes to this file where necessary
'''
def initialize_firebase_connection():
        firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        auth = firebase.auth()
        db = firebase.database()
        return db