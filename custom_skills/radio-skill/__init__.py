# Reference https://github.com/normandmickey/skill-internet-radio
import time
import vlc
import requests
import random
from mycroft.util.log import getLogger
from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills import MycroftSkill, skill_api_method
from mycroft.audio import wait_while_speaking
#skill api
from mycroft.skills.core import MycroftSkill, intent_handler, skill_api_method
#api skill get skill
from mycroft.skills.api import SkillApi
# Import mp3 skill
from mycroft.util import play_mp3

#Station URLS
CLASSIC = 'http://icecast.thisisdax.com/ClassicFMMP3.m3u'
HEART = 'http://icecast.thisisdax.com/HeartUKMP3.m3u'
SMOOTH = 'http://icecast.thisisdax.com/SmoothUKMP3.m3u'
CAPITAL = 'http://icecast.thisisdax.com/CapitalUKMP3.m3u'
LBC = 'http://icecast.thisisdax.com/LBCUKMP3Low.m3u'


class InternetRadioSkill(MycroftSkill):
    def __init__(self):
        super(InternetRadioSkill, self).__init__(name="InternetRadioSkill")
        self.process = None

        # Selection options for radio
        self.options = ['classic', 'heart', 'smooth', 'capital', 'lbc']
    

    @intent_file_handler('radio.intent')
    def handle_radio(self, message):

        self.stop()

        self.speak_dialog('Which station would you like to play?')
        selection = self.ask_selection(self.options, numeric=True).lower()

        try:
            

            if selection == self.options[0]:

                self.speak_dialog('Playing Classic FM')
                time.sleep(4)

                if CLASSIC[-3:] == 'm3u':
                    self.process = play_mp3(CLASSIC[:-4])
                else:
                    self.process = play_mp3(CLASSIC)


            elif selection == self.options[1]:
                
                self.speak_dialog('Playing Heart FM')
                time.sleep(4)

                if HEART[-3:] == 'm3u':
                    self.process = play_mp3(HEART[:-4])
                else:
                    self.process = play_mp3(HEART)


            elif selection == self.options[2]:

                self.speak_dialog('Playing Smooth Radio')
                time.sleep(4)

                if SMOOTH[-3:] == 'm3u':
                    self.process = play_mp3(SMOOTH[:-4])
                else:
                    self.process = play_mp3(SMOOTH)
            
            elif selection == self.options[3]:
 
                self.speak_dialog('Playing Capital Radio')
                time.sleep(4)

                if CAPITAL[-3:] == 'm3u':
                    self.process = play_mp3(CAPITAL[:-4])
                else:
                    self.process = play_mp3(CAPITAL)

            elif selection == self.options[4]:


                self.speak_dialog('Playing LBC')

                time.sleep(4)
                if LBC[-3:] == 'm3u':
                    self.process = play_mp3(LBC[:-4])
                else:
                    self.process = play_mp3(LBC)


            else:
                self.speak_dialog('Sorry I did not quite catch that')


        except:
            self.speak_dialog('Please try again')

    @intent_file_handler('stopradio.intent')
    def handle_stop(self, message):

        self.stop()
        self.speak_dialog('Stopping.the.radio')



    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process.wait()



def create_skill():
    return InternetRadioSkill()
