import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

from navigate import Navigate
from setup_tests import SetupTests


class Behaviour(object):

    def _get_location(self):
        # @ glyph should always exist and there should only be one
        location = self.navigate.get_map_feature('@')
        return location[0]

    def _get_path(self, goal):
        mylocation = self._get_location()
        self.mypath = self.navigate.get_path(mylocation, goal)

    def _path_interupted(self):
        print "path interupted"

    def _reached_path_goal(self):
        print "reached goal"

    def Update(self):
        raise ValueError('unimplimented behaviour update')

    # Each turn take a step towards the next path tile and pop it off
    #   the path
    # Call one function when we reach the goal and another if we get
    #   interupted
    def _follow_path(self):
        _mylocation = self._get_location()
        next_step = self.mypath.pop(0)
        if (abs(next_step[0] - _mylocation[0]) > 1 or
                abs(next_step[1] - _mylocation[1]) > 1):
            self.mypath = None
            self._path_interupted()
        else:
            self.move_to_tile(next_step)
            if len(self.mypath) == 0:
                self.mypath = None
                self._reached_path_goal()

    # Goal needs to be in the format (x, y)
    # Takes one step in the right direction
    def move_to_tile(self, goal):
        mylocation = self._get_location()
        print "my location", mylocation
        html_element = self.browser.find_element_by_tag_name('html')
        if mylocation[0] > goal[0] and mylocation[1] < goal[1]:
            html_element.send_keys('1')
        elif mylocation[0] == goal[0] and mylocation[1] < goal[1]:
            html_element.send_keys('2')
        elif mylocation[0] < goal[0] and mylocation[1] < goal[1]:
            html_element.send_keys('3')
        elif mylocation[0] > goal[0] and mylocation[1] == goal[1]:
            html_element.send_keys('4')
        elif mylocation[0] == goal[0] and mylocation[1] == goal[1]:
            html_element.send_keys('5')
        elif mylocation[0] < goal[0] and mylocation[1] == goal[1]:
            html_element.send_keys('6')
        elif mylocation[0] > goal[0] and mylocation[1] > goal[1]:
            html_element.send_keys('7')
        elif mylocation[0] == goal[0] and mylocation[1] > goal[1]:
            html_element.send_keys('8')
        elif mylocation[0] < goal[0] and mylocation[1] > goal[1]:
            html_element.send_keys('9')

    def __init__(self, browser, navigate):
        self.browser = browser
        self.mypath = None
        self.navigate = navigate


class FindDownStaircase(Behaviour):

    def _reached_path_goal(self):
        html_element = self.browser.find_element_by_tag_name('html')
        html_element.send_keys('>')

    def __path_interupted(self):
        print "path interupted"

    def Update(self):
        self.navigate.get_map(self.browser)
        print "in update"
        if self.mypath is None:
            goals = self.navigate.get_map_feature('>')
            if len(goals) != 0:
                Behaviour._get_path(self, goals[0])
            else:
                print "no down stairs to path to"
        else:
            Behaviour._follow_path(self)

    def __init__(self, browser, navigate):
        super(FindDownStaircase, self).__init__(browser, navigate)


# Placeholder behaviour for the many actions I havn't made behaviours yet
class Dummy(Behaviour):
    def Update(self):
        return

    def __init__(self, browser):
        super(Dummy, self).__init__(browser)

  
if __name__ == "__main__":
    browser = SetupTests.setup()
    navigate = Navigate(browser)
    behaviour = FindDownStaircase(browser, navigate)
    while True:
        # Lag will mess this up if its too lower
        # When actually playing use the turncount change check in derpyai
        time.sleep(0.5)
        behaviour.Update()
