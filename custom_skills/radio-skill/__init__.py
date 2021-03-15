
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
# Import audio skill
from mycroft.skills.audioservice import AudioService

# Reference https://github.com/normandmickey/skill-internet-radio
class InternetRadioSkill(MycroftSkill):
    def __init__(self):
        super(InternetRadioSkill, self).__init__(name="InternetRadioSkill")
        self.audioservice = None
        self.process = None


    def initialize(self):
        self.audio_service = AudioService(self.bus)


    @intent_file_handler('radio.intent')
    def handle_radio(self, message):
        self.stop() #Stop incase radio is currently playing

        self.speak_dialog('What BBC radio station would you like to play? One, two, three, four, or five live')

        time.sleep(10)



        try:
            chosen_station = self.get_response().lower()

            if chosen_station == '1' or chosen_station == 'one':

                self.speak_dialog('Playing BBC Radio 1')
                time.sleep(4)
                self.audio_service.play("https://redirect.viglink.com/?format=go&jsonp=vglnk_161575420247533&key=8ace3fc8b4830d32ead5520650c6ce6e&libId=km9k2eff01000ad7000DLu95eo64a3cwo&loc=https%3A%2F%2Fwww.hifiwigwam.com%2Fforum%2Ftopic%2F127134-high-quality-320kbps-streams-for-all-bbc-radio-stations%2F&v=1&out=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_one.m3u8&title=High%20Quality%20320kbps%20streams%20for%20all%20BBC%20radio%20stations%20-%202%20Channel%20-%20HiFi%20WigWam&txt=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_one.m3u8")


            elif chosen_station == '2' or chosen_station == 'two':

                self.speak_dialog('Playing BBC Radio 2')
                time.sleep(4)



                self.audio_service.play("https://redirect.viglink.com/?format=go&jsonp=vglnk_161575421242234&key=8ace3fc8b4830d32ead5520650c6ce6e&libId=km9k2eff01000ad7000DLu95eo64a3cwo&loc=https%3A%2F%2Fwww.hifiwigwam.com%2Fforum%2Ftopic%2F127134-high-quality-320kbps-streams-for-all-bbc-radio-stations%2F&v=1&out=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_two.m3u8&title=High%20Quality%20320kbps%20streams%20for%20all%20BBC%20radio%20stations%20-%202%20Channel%20-%20HiFi%20WigWam&txt=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_two.m3u8")

            elif chosen_station == '3' or chosen_station == 'three':

                self.speak_dialog('Playing BBC Radio 3')
                time.sleep(4)



                self.audio_service.play("https://redirect.viglink.com/?format=go&jsonp=vglnk_161575422526535&key=8ace3fc8b4830d32ead5520650c6ce6e&libId=km9k2eff01000ad7000DLu95eo64a3cwo&loc=https%3A%2F%2Fwww.hifiwigwam.com%2Fforum%2Ftopic%2F127134-high-quality-320kbps-streams-for-all-bbc-radio-stations%2F&v=1&out=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_three.m3u8&title=High%20Quality%20320kbps%20streams%20for%20all%20BBC%20radio%20stations%20-%202%20Channel%20-%20HiFi%20WigWam&txt=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_three.m3u8")

            
            elif chosen_station == '4' or chosen_station == 'four':      
                self.speak_dialog('Playing BBC Radio 4')
                time.sleep(4)



                self.audio_service.play("https://redirect.viglink.com/?format=go&jsonp=vglnk_161575415916532&key=8ace3fc8b4830d32ead5520650c6ce6e&libId=km9k2eff01000ad7000DLu95eo64a3cwo&loc=https%3A%2F%2Fwww.hifiwigwam.com%2Fforum%2Ftopic%2F127134-high-quality-320kbps-streams-for-all-bbc-radio-stations%2F&v=1&out=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_four_extra.m3u8&title=High%20Quality%20320kbps%20streams%20for%20all%20BBC%20radio%20stations%20-%202%20Channel%20-%20HiFi%20WigWam&txt=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_four_extra.m3u8")

            elif chosen_station == '5' or chosen_station == 'five' or chosen_station == '5 live' or chosen_station == 'five live' or chosen_station == 'live':

                self.speak_dialog('Playing BBC Radio 5 Live')
                time.sleep(4)



                self.audio_service.play("https://redirect.viglink.com/?format=go&jsonp=vglnk_161575424224036&key=8ace3fc8b4830d32ead5520650c6ce6e&libId=km9k2eff01000ad7000DLu95eo64a3cwo&loc=https%3A%2F%2Fwww.hifiwigwam.com%2Fforum%2Ftopic%2F127134-high-quality-320kbps-streams-for-all-bbc-radio-stations%2F&v=1&out=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_five_live.m3u8&title=High%20Quality%20320kbps%20streams%20for%20all%20BBC%20radio%20stations%20-%202%20Channel%20-%20HiFi%20WigWam&txt=http%3A%2F%2Fa.files.bbci.co.uk%2Fmedia%2Flive%2Fmanifesto%2Faudio%2Fsimulcast%2Fhls%2Fuk%2Fsbr_high%2Fak%2Fbbc_radio_five_live.m3u8")

            else:
                self.speak_dialog('Sorry I did not quite catch that')


        except:
            self.speak_dialog('Please try again')


    @intent_file_handler('stopradio.intent')
    def handle_stop(self, message):
        self.stop()
        self.speak_dialog('Stopping.the.radio')

    def stop(self):
           self.audio_service.stop()

def create_skill():
    return InternetRadioSkill()