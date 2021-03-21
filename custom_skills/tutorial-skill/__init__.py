from mycroft import MycroftSkill, intent_file_handler


CONTACTING_INFO = 'You can contact a family member or friend via email or text message., Make sure you have added them as a contact via the mobile app., To send a text message, say "Send a message", and to send an email, say "send an email"., You will then be asked which contact you would like to send it to, Finally, you will then be asked for the message, and to confirm it before sending.'

RADIO_INFO = 'You can listen to the radio by saying "listen to the radio", . You will then be asked to confirm which station you would like to play from a list of options'

NEWS_INFO = 'To subscribe to a news topic, say, "subscribe to a topic", and unsubscribe with, "unsubscribe from, topic" ,. You can get your subscribed topics with, "tell me my topics" ., To hear the latest news on your personal user topics, please say "tell me my news", and if you would like news on a specific topic, for example, sports, say "give me the news on, sports"., If you would like to hear about an article in more detail, say, "Read article name in detail"'

CALENDER_INFO = 'There are several commands you can use for reminders,. You can ask., "What is my next reminder",. "get all reminders for this monday" ,. "get all reminders for this week" ,. "clear all reminders" , or "cancel all reminders for tomorrow",. For calender events you can say,. "what is my next calender event" ,. "get the calender events for today or tomorrow" ,. "Get the calender events for this monday" ,. or, "get calender events for this week"'

class Tutorial(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)



        self.options = ['Contacting a friend or family member', 'Playing the radio', 'Reading the news', 'Calender events']

    @intent_file_handler('tutorial.intent')
    def handle_tutorial(self, message):
        self.speak_dialog('tutorial')

        selection = self.ask_selection(self.options, numeric=True, dialog='Which.would.you.like.information.on')

        if selection == self.options[0]:

            self.speak_dialog(CONTACTING_INFO)

        elif selection == self.options[1]:

            self.speak_dialog(RADIO_INFO)

        elif selection == self.options[2]:

            self.speak_dialog(NEWS_INFO)
        
        elif selection == self.options[3]:

            self.speak_dialog(CALENDER_INFO)

        else:

            self.speak_dialog("I didn't quite catch that")

        




def create_skill():
    return Tutorial()

