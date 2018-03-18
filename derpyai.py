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
# Load username and password from file
login_info = open('login.txt', 'r').read()
login_info = dict(x.split(':') for x in login_info.split('\n'))
# Enter username and password
element = wait.until(EC.element_to_be_clickable((By.ID, 'username')))
element.send_keys(login_info['username'])
element = browser.find_element_by_name('password')
element.send_keys(login_info['password'] + Keys.RETURN)


##############################################################################
#           Enter Game, Select Character
##############################################################################
# Code to select a crawl version and select a character
# Called here, and after the player dies
def enter_game():
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
enter_game()


##############################################################################
#           Gameplay
##############################################################################
# Return the last message the game printed by the game
def get_last_message():
    with lock:
        elements = browser.find_elements_by_class_name('game_message')
        return (elements[len(elements) - 1]).get_attribute('innerHTML')


# Takes the turn we started the game loop on
# Returns when it has changed so we know when to take another turn
def wait_for_turn_advancement(turncount):
    retry_count = 0
    max_retrys = 20
    # Wait for the turn count to change before continuing
    while True:
        # For now there's a lot of ways this can get locked
        # So for now just try playing again if we've waited too long
        retry_count += 1
        if retry_count > max_retrys:
            print "waited too long for next turn, unblocking"
            break
        try:
            with lock:
                newturncount = (browser.find_element_by_id('stats_time').
                                get_attribute('innerHTML'))
            if turncount != newturncount:
                break
        except selenium.common.exceptions.NoSuchElementException:
            # Triggers when the game exits
            break
        except selenium.common.exceptions.StaleElementReferenceException:
            # Also triggers when the game exits sometimes
            break
        time.sleep(0.1)
    print "Next turn!"


# Return if a threat is nearby
# Todo: think about what I really want out of this
# For now just return the total number of threats
def check_threats():
    try:
        with lock:
            enemies = browser.find_elements_by_xpath(
                            "//span[contains(@class, 'hostile')]")
            print "number of enemies", len(enemies)
            for enemy in enemies:
                print enemy.get_attribute("class")
            return len(enemies)
    except selenium.common.exceptions.NoSuchElementException:
        print "no enemies found"
        return 0


# Lets us know if our health isn't full so we know when to rest
def get_player_health_full():
    with lock:
        current_hp = (browser.find_element_by_id("stats_hp").
                      get_attribute("innerHTML"))
        max_hp = (browser.find_element_by_id("stats_hp_max").
                  get_attribute("innerHTML"))
    print "hp {0} out of {1}".format(current_hp, max_hp)
    return current_hp == max_hp


def stuck_check(more_message, menu, lock, html_element):
    # Periodically check for messages that lock the game
    while True:
        # If the player died kill this thread
        # Re-make it once back in the game
        global dead_state
        if dead_state:
            print "killing thread"
            return
        with lock:
            print "html element", html_element
            print "checking stuck", more_message.get_attribute('style')
            # More message is hidden unless I need to make it go away.
            # Style changes to none when visible
            if ('hidden' not in more_message.get_attribute('style') and
                    'none' not in more_message.get_attribute('style')):
                print "more message, pressing enter"
                html_element.send_keys(Keys.RETURN)
            # Some things (shops) force the menu open
            # So see if the menu is open then just close it
            if ('hidden' not in menu.get_attribute('style') and
                    'none' not in menu.get_attribute('style')):
                print "menu open, pressing escape"
                html_element.send_keys(Keys.ESCAPE)
        message = get_last_message()
        print "last message:", message
        if "Increase (S)trength, (I)ntelligence, or (D)exterity?" in message:
            # If we got a stat up always level dex.
            with lock:
                html_element.send_keys('D')
        if "You die..." in message:
            # When dead this will hit enter until we exit back to lobby
            with lock:
                html_element.send_keys(Keys.RETURN)
        time.sleep(1)


def start_stuck_check():
    with lock:
        more_message = browser.find_element_by_id('more')
        menu = browser.find_element_by_id('menu')
        html_element = browser.find_element_by_tag_name('html')
    stuck_thread = threading.Thread(
                    target=stuck_check,
                    args=(more_message, menu, lock, html_element, ))
    stuck_thread.setDaemon(True)
    stuck_thread.start()

# Tracks if the player dies and we're in the lobby again
dead_state = False
# Selenium is not thread safe
# Any selenium functions, even just getting attributes, need to be locked
lock = threading.RLock()
start_stuck_check()
with lock:
    # Get the html element to send key presses to the whole page
    html_element = browser.find_element_by_tag_name('html')
# Main gameplay loop
while True:
    # Check if the player died, restart the game if so
    if dead_state:
        enter_game()
        dead_state = False
        start_stuck_check()
    # Record the current turn, so we know when the it goes up later
    # If this no longer exists we are dead and need to re-enter the game
    try:
        with lock:
            turncount = (browser.find_element_by_id('stats_time').
                         get_attribute('innerHTML'))
    except selenium.common.exceptions.NoSuchElementException:
        dead_state = True
        continue
    num_enemies = check_threats()
    last_message = get_last_message()
    # Enter commands for the player
    with lock:
        if num_enemies > 0:
            # Auto fight when enemies are around
            # Will need to be replaced with my own pathfinding someday
            html_element.send_keys(Keys.TAB)
        elif ('There is a lethal amount of poison in your body!'
                in last_message):
            # We have already been poisoned to death, just wait to die
            # I'll figure out item use later
            html_element.send_keys('.')
        elif not get_player_health_full():
            # Rest if we are hurt
            html_element.send_keys('5')
        elif 'explor' in last_message:
            # Check if we're done exploring or partially explored
            # Try to go down the nearest staircase if so
            html_element.send_keys(Keys.LEFT_SHIFT + 'X')
            # I don't have a better way to see if that commands
            #   triggered at the moment, so just wait a second
            # If the server lags enough this will mess up
            time.sleep(1)
            html_element.send_keys(Keys.LEFT_SHIFT + '>')
            time.sleep(1)
            html_element.send_keys(Keys.RETURN)
            time.sleep(1)
            html_element.send_keys('>')
        else:
            # Explore if nothing else is going on
            html_element.send_keys('o')
    wait_for_turn_advancement(turncount)
