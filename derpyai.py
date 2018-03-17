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
#           login
##############################################################################
#load username and password from file
login_info = open('login.txt','r').read()
login_info = dict(x.split(':') for x in login_info.split('\n'))
#enter username and password
element = wait.until(EC.element_to_be_clickable((By.ID, 'username')))
element.send_keys(login_info['username'])
element = browser.find_element_by_name('password')  # Find the search box
element.send_keys(login_info['password'] + Keys.RETURN)
##############################################################################
#           enter game, select character
##############################################################################
#code to select a crawl version and select a character
#called here, and after the player dies
def enter_game():
    #start playing the latest stable version of crawl
    element = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, '(Latest Version!)')))
    element.send_keys(Keys.RETURN)
    #character select
    #select felid berseker every time, for easier decision making
    #a class titled fg14 means we're in the menu
    #existance of a game_message means we're already in the game 
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
enter_game()
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
        #for now there's a lot of ways this can get locked
        #so for now just try playing again if we've waited too long 
        retry_count += 1
        if retry_count > max_retrys:
            print "waited too long for next turn, unblocking"
            break
        #print "waiting on turn count"
        try:
            with lock:
                newturncount = browser.find_element_by_id('stats_time').get_attribute('innerHTML')
            if turncount != newturncount:
                break
        except selenium.common.exceptions.NoSuchElementException:
            #triggers when the game exits
            break
        except selenium.common.exceptions.StaleElementReferenceException:
            #also triggers when the game exits sometimes
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
    #periodically check for messages that lock the game
    while True:
        #if the player died kill this thread
        #re-make it once back in the game
        global dead_state
        if dead_state:
            print "killing thread"
            return
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
        print "last message:", message
        if "Increase (S)trength, (I)ntelligence, or (D)exterity?" in message:
            #if we got a stat up always level dex.
            with lock:
                element.send_keys('D')
        if "You die..." in message:
            #when dead this will hit enter until we exit back to lobby
            with lock:
                element.send_keys(Keys.RETURN)
        time.sleep(1)

def start_stuck_check(lock):
    with lock:
        more_message = browser.find_element_by_id('more')
    stuck_thread = threading.Thread(target=stuck_check, args=(more_message, lock,))
    stuck_thread.setDaemon(True)
    stuck_thread.start()
        
#tracks if the player dies and we're in the lobby again
dead_state = False
#selenium is not thread safe
#any selenium functions, even just getting attributes, need to be locked
lock = threading.RLock()
start_stuck_check(lock)           
with lock:
    #get the html element to send key presses to the whole page
    html_element = browser.find_element_by_tag_name('html')  
#main gameplay loop
while True:
    #check if the player died, restart the game if so
    if dead_state:
        enter_game()
        dead_state = False
        start_stuck_check(lock)
    #record the current turn, so we know when the it goes up later
    #if this no longer exists we are dead and need to re-enter the game
    try:
        with lock:
            turncount = browser.find_element_by_id('stats_time').get_attribute('innerHTML')
    except selenium.common.exceptions.NoSuchElementException:
        dead_state = True
        continue
    num_enemies = check_threats()
    with lock:
        if num_enemies > 0:
            html_element.send_keys(Keys.TAB)
        else:
            html_element.send_keys('o')
    wait_for_turn_advancement(turncount)