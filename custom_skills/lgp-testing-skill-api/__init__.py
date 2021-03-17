# TODO: Add an appropriate license to your skill before publishing.  See
# the LICENSE file for more information.

# Below is the list of outside modules you'll be using in your skill.
# They might be built-in to Python, from mycroft-core or from external
# libraries.  If you use an external library, be sure to include it
# in the requirements.txt file so the library is installed properly
# when the skill gets installed later by a user.

from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills.api import SkillApi


class TestingSkillApi(MycroftSkill):

    def __init__(self):
        super(TestingSkillApi, self).__init__()

    @intent_file_handler("TestSkillApi.intent")
    def handle_hello_world_intent(self, message):
        print("I am calling the skill api method")
        my_skill = SkillApi.get('mycroft-joke.mycroftai')
        my_skill.speak_joke('en', 'neutral')


def create_skill():
    return TestingSkillApi()
