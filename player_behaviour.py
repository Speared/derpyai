import threading
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

from navigate import Navigate

class Behaviour(object):

    def _get_location(self):
        # @ glyph should always exist and there should only be one
        return self.navigate.get_map_feature('@')[0]
 
 
    def _get_path(self, goal):
        mylocation = self._get_location()
        self.mypath = self.navigate.get_path(mylocation, goal)
 
    
    def _path_interupted(self):
        print "path interupted"
        
    def _reached_path_goal(self):
        print "reached goal"
    
    def Update(self):
        raise ValueError('unimplimented behavious update')
    
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
        with self.lock:
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
    
    def __init__(self, browser, lock):
        self.browser = browser
        self.lock = lock
        self.mypath = None
        self.navigate = Navigate()


class FindDownStaircase(Behaviour):

    def _reached_path_goal(self):
        html_element = self.browser.find_element_by_tag_name('html')
        html_element.send_keys('>')
    
    def __path_interupted(self):
        print "path interupted"

    def Update(self):
        self.navigate.get_map(self.browser)
        if self.mypath is None:
            goals = self.navigate.get_map_feature('>')
            if len(goals) != 0:
                Behaviour._get_path(self, goals[0])
            else:
                print "no down stairs to path to"
        else:
            Behaviour._follow_path(self)
        

    def __init__(self, browser, lock):
         super(FindDownStaircase, self).__init__(browser, lock)

def _tests(browser):
    lock = threading.RLock()
    behaviour = FindDownStaircase(browser, lock)
    
    while True:
        # Lag will mess this up if its too lower
        # When actually playing use the turncount change check in derpyai
        time.sleep(0.5)
        behaviour.Update()
         
# TODO: make this block of code in its own file so I don't 
#   have to copy/paste it everywhere  
if __name__ == "__main__":
    
    # Open crawl, enter the game and try to get a map for test purposes
    # Copy/pasted from derpyai.py
    browser = webdriver.Chrome()
    browser.get('http://crawl.berotato.org:8080/#lobby')
    wait = WebDriverWait(browser, 60)
    # Get login info
    login_info = open('login.txt', 'r').read()
    login_info = dict(x.split(':') for x in login_info.split('\n'))
    # Enter username/password
    element = wait.until(EC.element_to_be_clickable((By.ID, 'username')))
    element.send_keys(login_info['username'])
    element = browser.find_element_by_name('password')
    element.send_keys(login_info['password'] + Keys.RETURN)
    # Start playing the latest stable version of crawl
    element = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT,
                                                    '(Latest Version!)')))
    element.send_keys(Keys.RETURN)
    # Character select
    # Select felid berseker every time, for easier decision making
    # A class titled fg14 means we're in the menu
    # Existance of a game_message means we're already in the game
    wait.until((EC.presence_of_element_located((By.CSS_SELECTOR,
                                                '.fg14, .game_message'))))
    try:
        if browser.find_element_by_xpath('//*[@id="crt"]/span[1]/span[2]'):
            print "selecting character"
            element = browser.find_element_by_tag_name('html')
            element.send_keys('y')
            wait.until(EC.text_to_be_present_in_element(
                        (By.XPATH, '//*[@id="crt"]/span[1]/span[2]'),
                        'Please select your background.'))
            element = browser.find_element_by_tag_name('html')
            element.send_keys('e')
            # Now that we're logged in wait for the first game message
            wait.until(EC.presence_of_element_located(
                        (By.CLASS_NAME, 'game_message')))
    except selenium.common.exceptions.NoSuchElementException:
        pass
    _tests(browser)
    
    
