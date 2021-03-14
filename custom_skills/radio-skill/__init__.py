
import time
import vlc
import requests
import random
from mycroft.util.log import getLogger
from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills import MycroftSkill, skill_api_method

#skill api
from mycroft.skills.core import MycroftSkill, intent_handler, skill_api_method
#api skill get skill
from mycroft.skills.api import SkillApi

from mycroft.skills.audioservice import AudioService


# try:
#     from mycroft.skills.audioservice import AudioService
# except:
#     from mycroft.util import play_mp3
#     AudioService = None



__author__ = 'nmoore'


LOGGER = getLogger(__name__)


class InternetRadioSkill(MycroftSkill):
    def __init__(self):
        super(InternetRadioSkill, self).__init__(name="InternetRadioSkill")
        self.audioservice = None
        self.process = None


    def initialize(self):


        
        self.audio_service = AudioService(self.bus)

        

    @intent_file_handler('bbcradio1.intent')
    def handle_bbcradio1(self, message):
        self.stop()
        self.speak_dialog('Playing.the.radio')
        time.sleep(4)



        self.audio_service.play('https://redirect.viglink.com/?format=go&jsonp=vglnk_161541752509712&key=8ace3fc8b4830d32ead5520650c6ce6e&libId=km41vroy01000ad7000DLbfwrh5yh&loc=https%3A%2F%2Fwww.hifiwigwam.com%2Fforum%2Ftopic%2F127134-high-quality-320kbps-streams-for-all-bbc-radio-stations%2F&v=1&out=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_one.m3u8&ref=https%3A%2F%2Fwww.google.com%2F&title=High%20Quality%20320kbps%20streams%20for%20all%20BBC%20radio%20stations%20-%202%20Channel%20-%20HiFi%20WigWam&txt=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_one.m3u8')                               

            

            


    

    @intent_file_handler('stopradio.intent')
    def handle_stop(self, message):
        self.stop()
        self.speak_dialog('Stopping.the.radio')

    def stop(self):
        if self.audio_service:
           self.audio_service.stop()
        else:
            if self.process and self.process.poll() is None:
               self.process.terminate()
               self.process.wait()

def create_skill():
    return InternetRadioSkill()