import time
import threading

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

browser = webdriver.Chrome()
wait = WebDriverWait(browser, 60)
browser.get('http://crawl.berotato.org:8080/#lobby')
##############################################################################
#           Login
##############################################################################
#load username and password from file
login_info = open('login.txt','r').read()
login_info = dict(x.split(':') for x in login_info.split('\n'))
#enter username and password
element = wait.until(EC.element_to_be_clickable((By.ID, 'username')))
element.send_keys(login_info['username'])
element = browser.find_element_by_name('password')  # Find the search box
element.send_keys(login_info['password'] + Keys.RETURN)
#start playing the latest stable version of crawl
element = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, '(Latest Version!)')))
element.send_keys(Keys.RETURN)
##############################################################################
#           character select
##############################################################################
#select felid berseker every time, for easier decision making
#a class titled fg14 means we're in the menu
#existance of a game_message means we're already in the game and can skip this
wait.until((EC.presence_of_element_located((By.CSS_SELECTOR, '.fg14, .game_message'))))  
try:                
    if browser.find_element_by_xpath('//*[@id="crt"]/span[1]/span[2]'):  
        print "selecting character"
        element = browser.find_element_by_tag_name('html')
        element.send_keys('y')
        wait.until(EC.text_to_be_present_in_element((By.XPATH,
                                                    '//*[@id="crt"]/span[1]/span[2]'), 
                                                    'Please select your background.'))
        element = browser.find_element_by_tag_name('html')
        element.send_keys('e')
        #now that we're logged in wait for the first game message
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'game_message')))
except selenium.common.exceptions.NoSuchElementException:
    pass

##############################################################################
#           gameplay
##############################################################################
print "made it to the game!"
#return the last message the game printed by the game
def get_last_message():
    #print "\nmessages"
    with lock:
        elements = browser.find_elements_by_class_name('game_message')
        return (elements[len(elements) - 1]).get_attribute('innerHTML')

#takes the turn we started the game loop on
#returns when it has changed so we know when to take another turn
def wait_for_turn_advancement(turncount):
    retry_count = 0
    max_retrys = 20
    #wait for the turn count to change before continuing 
    while True:
        #for now there's a lot of ways this can get locked waiting for a new turn
        #so for now just try playing again if we've waited too long 
        retry_count += 1
        if retry_count > max_retrys:
            print "waited too long for next turn, unblocking"
            break
        print "waiting on turn count"
        with lock:
            newturncount = browser.find_element_by_id('stats_time').get_attribute('innerHTML')
        if turncount != newturncount:
            break
        time.sleep(0.1)
    print "Next turn!"

#return if a threat is nearby
#todo: think about what I really want out of this. 
#for now just return the total number of threats 
def check_threats():
    try:
        with lock:
            enemies = browser.find_elements_by_xpath("//span[contains(@class, 'hostile')]")
            print "number of enemies", len(enemies)
            for enemy in enemies:
                print enemy.get_attribute("class")
            return len(enemies)
    except selenium.common.exceptions.NoSuchElementException:
        print "no enemies found"
        return 0

def stuck_check(more_message, lock):
    #periodically check for messages that lock the game and get rid of them
    while True:
        #more message is hidden unless I need to make it go away.
        #style changes to none when visible
        with lock:
            element = browser.find_element_by_tag_name('html')
            print "checking stuck", more_message.get_attribute('style')
            if ('hidden' not in more_message.get_attribute('style') 
                    and 'none' not in more_message.get_attribute('style')):
                print "more message, pressing enter"
                element.send_keys(Keys.RETURN)
        message = get_last_message()
        if "Increase (S)trength, (I)ntelligence, or (D)exterity?" in message:
            #if we got a stat up always level dex.
            with lock:
                element.send_keys('D')
        time.sleep(1)

#selenium is not thread safe
#any selenium functions, even just getting attributes, need to be locked
lock = threading.RLock()           
more_message = browser.find_element_by_id('more')
stuck_thread = threading.Thread(target=stuck_check, args=(more_message, lock,))
stuck_thread.setDaemon(True)
stuck_thread.start()
#main gameplay loop
while True:
    with lock:
        #get the html element to send key presses to the whole page
        element = browser.find_element_by_tag_name('html')     
    #record the current turn, so we know when the turncount goes up later
    with lock:
        turncount = browser.find_element_by_id('stats_time').get_attribute('innerHTML')     
    num_enemies = check_threats()
    with lock:
        if num_enemies > 0:
            element.send_keys(Keys.TAB)
        else:
            element.send_keys('o')
    wait_for_turn_advancement(turncount)