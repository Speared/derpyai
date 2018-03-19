import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

from player_behaviour import FindDownStaircase

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
    elements = browser.find_elements_by_class_name('game_message')
    return (elements[len(elements) - 1]).get_attribute('innerHTML')


# Takes the turn we started the game loop on
# Returns when it has changed so we know when to take another turn
def wait_for_turn_advancement(turncount):
    retry_count = 0
    max_retrys = 200
    # Wait for the turn count to change before continuing
    while True:
        if not stuck_check():
            return
        # For now there's a lot of ways this can get locked
        # So for now just try playing again if we've waited too long
        retry_count += 1
        if retry_count > max_retrys:
            print "waited too long for next turn, unblocking"
            break
        try:
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
        enemies = browser.find_elements_by_xpath(
                        "//span[contains(@class, 'hostile')]")
        print "number of enemies", len(enemies)
        numstale = 0
        for enemy in enemies:
            try:
                print enemy.get_attribute("class")
            except selenium.common.exceptions.StaleElementReferenceException:
                # Sometimes triggers right after killing an enemy
                # Just make a note that this enemy dosn't exist
                print "stale enemy found"
                numstale += 1
        return len(enemies) - numstale
    except selenium.common.exceptions.NoSuchElementException:
        print "no enemies found"
        return 0


# Lets us know if our health isn't full so we know when to rest
def get_player_health_full():
    current_hp = (browser.find_element_by_id("stats_hp").
                  get_attribute("innerHTML"))
    max_hp = (browser.find_element_by_id("stats_hp_max").
              get_attribute("innerHTML"))
    print "hp {0} out of {1}".format(current_hp, max_hp)
    return current_hp == max_hp


def stuck_check():
    # Check for messages that lock the game
    # Called by the function that locks our controlls while waiting for
    #   the turncount to advance. Returns true if it did anything to 
    #   un-stuck the game to flag that we can unlock the controlls and 
    #   try moving again
    global dead_state
    try:
        print "html element", html_element
        try:
            more_message = browser.find_element_by_id('more')
            menu = browser.find_element_by_id('menu')
        except selenium.common.exceptions.NoSuchElementException:
            # These elements being gone means we're in the lobby
            # Flag that we need to re-enter game
            dead_state = True
            return True
        print "checking stuck", more_message.get_attribute('style')
        # More message is hidden unless I need to make it go away.
        # Style changes to none when visible
        if ('hidden' not in more_message.get_attribute('style') and
                'none' not in more_message.get_attribute('style')):
            print "more message, pressing enter"
            html_element.send_keys(Keys.RETURN)
            return True
        # Some things (shops) force the menu open
        # So see if the menu is open then just close it
        if ('hidden' not in menu.get_attribute('style') and
                'none' not in menu.get_attribute('style')):
            print "menu open, pressing escape"
            html_element.send_keys(Keys.ESCAPE)
            return True
        message = get_last_message()
        print "last message:", message
        if "Increase (S)trength, (I)ntelligence, or (D)exterity?" in message:
            # If we got a stat up always level dex.
            html_element.send_keys('D')
            return True
        if "You die..." in message:
            # When dead this will hit enter until we exit back to lobby
            html_element.send_keys(Keys.RETURN)
            return True
        return False
    except selenium.common.exceptions.StaleElementReferenceException:
        # Hitting this error means we're in the loby again
        # Flag that we need to re-enter game
        dead_state = True
        return True


# Tracks if the player dies and we're in the lobby again
dead_state = False
# Get the html element to send key presses to the whole page
html_element = browser.find_element_by_tag_name('html')
# Eventually all player actions should be wrapped up in states
# With the state only being changed under some conditions
# For now this is the only playerstate we have, so updating it when we
#   need it is good enough
state = FindDownStaircase(browser)
# Main gameplay loop
while True:
    # Check if the player died, restart the game if so
    if dead_state:
        enter_game()
        dead_state = False
        state = FindDownStaircase(browser)
    # Record the current turn, so we know when the it goes up later
    # If this no longer exists we are dead and need to re-enter the game
    try:
        turncount = (browser.find_element_by_id('stats_time').
                     get_attribute('innerHTML'))
    except selenium.common.exceptions.NoSuchElementException:
        dead_state = True
        continue
    num_enemies = check_threats()
    last_message = get_last_message()
    # Enter commands for the player
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
        state.Update()
    else:
        # Explore if nothing else is going on
        html_element.send_keys('o')

    wait_for_turn_advancement(turncount)
