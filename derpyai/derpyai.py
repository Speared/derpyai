# Import built-in modules
import time

# Import third-party modules
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

# Import local modules
from login import get_login
from player_behaviour import FindDownStaircase
from navigate import Navigate


class DerpyAi(object):
    """Ai that plays dungeon crawl!"""

    def __init__(self):
        # Load username and password from file
        self.login_info = get_login()

        self.browser = webdriver.Chrome()
        self.wait = WebDriverWait(self.browser, 60)

        # Tracks if the player dies and we're in the lobby again
        self.dead_state = False
        # Get the html element to send key presses to the whole page
        self.html_element = self.browser.find_element_by_tag_name('html')
        self.navigate = Navigate(self.browser)
        # Eventually all player actions should be wrapped up in states
        # With the state only being changed under some conditions
        # For now this is the only playerstate we have, so updating it when we
        #   need it is good enough
        self.state = FindDownStaircase(self.browser, self.navigate)

    def login(self):
        """Log into our user"""
        element = self.wait.until(EC.element_to_be_clickable((By.ID, 'username')))
        element.send_keys(self.login_info['username'])
        element = self.browser.find_element_by_name('password')
        element.send_keys(self.login_info['password'] + Keys.RETURN)

    def enter_game(self):
        """Select a crawl version and select a character."""
        # Start playing the latest stable version of crawl
        element = self.wait.until(
            EC.element_to_be_clickable(
                # TODO: This is really hardcoded
                # That said, different servers have a different way
                # to mark the latest version, so dunno what to
                # actually look for currently.
                (By.PARTIAL_LINK_TEXT, 'Play 0.24')
            )
        )
        element.send_keys(Keys.RETURN)
        # Character select
        # Select felid berseker every time, for easier decision making
        # A class titled fg14 means we're in the menu
        # Existence of a game_message means we're already in the game
        self.wait.until((EC.presence_of_element_located((By.CSS_SELECTOR,
                                                    '.fg14, .game_message'))))
        try:
            if self.browser.find_element_by_xpath('//*[@id="crt"]/span[1]/span[2]'):
                print "selecting character"
                element = self.browser.find_element_by_tag_name('html')
                element.send_keys('y')
                self.wait.until(EC.text_to_be_present_in_element(
                            (By.XPATH, '//*[@id="crt"]/span[1]/span[2]'),
                            'Please select your background.'))
                element = self.browser.find_element_by_tag_name('html')
                element.send_keys('e')
                # Now that we're logged in wait for the first game message
                self.wait.until(EC.presence_of_element_located(
                            (By.CLASS_NAME, 'game_message')))
        except selenium.common.exceptions.NoSuchElementException:
            pass

    def get_last_message(self):
        """Return the last message printed by the game."""
        elements = self.browser.find_elements_by_class_name('game_message')
        return (elements[len(elements) - 1]).get_attribute('innerHTML')

    def wait_for_turn_advancement(self, turncount):
        """Wait until the turn changes, then return.

        This lets us know when we can push more buttons.

        Args:
            turncount (str): Current turn number.

        """
        retry_count = 0
        max_retrys = 200
        # Wait for the turn count to change before continuing
        while True:
            if not self.stuck_check():
                return
            # For now there's a lot of ways this can get locked
            # So for now just try playing again if we've waited too long
            retry_count += 1
            if retry_count > max_retrys:
                print "waited too long for next turn, unblocking"
                break
            try:
                newturncount = (self.browser.find_element_by_id('stats_time').
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
        print "Next turn!", newturncount

    # Return if a threat is nearby
    # Todo: think about what I really want out of this
    # For now just return the total number of threats
    def check_threats(self):
        """Get number of nearby threats.

        Returns:
            int: Number of nearby threats.

        """
        try:
            enemies = self.browser.find_elements_by_xpath(
                "//span[contains(@class, 'hostile')]"
            )
            numstale = 0
            for enemy in enemies:
                try:
                    enemy.get_attribute("class")
                except selenium.common.exceptions.StaleElementReferenceException:
                    # Sometimes triggers right after killing an enemy
                    # Just make a note that this enemy dosn't exist
                    numstale += 1
            return len(enemies) - numstale
        except selenium.common.exceptions.NoSuchElementException:
            return 0

    def get_player_health_full(self):
        """Get if the player's health is full.

        This lets us know if our health isn't full so we know when to rest.

        Returns:
            bool: True if the player's health is full, otherwise False.

        """
        current_hp = (self.browser.find_element_by_id("stats_hp").
                      get_attribute("innerHTML"))
        max_hp = (self.browser.find_element_by_id("stats_hp_max").
                  get_attribute("innerHTML"))
        return current_hp == max_hp

    def stuck_check(self):
        """Check for messages that lock the game and try to deal with them.

        Called by the function that locks our contrails while waiting for
        the turncount to advance.

        Returns:
            bool: True if this did anything to un-stuck the game to flag that
                we can unlock the controls and try moving again.

        """
        try:
            try:
                more_message = self.browser.find_element_by_id('more')
                menu = self.browser.find_element_by_id('menu')
            except selenium.common.exceptions.NoSuchElementException:
                # These elements being gone means we're in the lobby
                # Flag that we need to re-enter game
                self.dead_state = True
                return True
            # More message is hidden unless I need to make it go away.
            # Style changes to none when visible
            if ('hidden' not in more_message.get_attribute('style') and
                    'none' not in more_message.get_attribute('style')):
                print "more message, pressing enter"
                self.html_element.send_keys(Keys.RETURN)
                return True
            # Some things (shops) force the menu open
            # So see if the menu is open then just close it
            if ('hidden' not in menu.get_attribute('style') and
                    'none' not in menu.get_attribute('style')):
                print "menu open, pressing escape"
                self.html_element.send_keys(Keys.ESCAPE)
                return True
            message = self.get_last_message()
            if "Increase (S)trength, (I)ntelligence, or (D)exterity?" in message:
                # If we got a stat up always level dex.
                self.html_element.send_keys('D')
                return True
            if "You die..." in message:
                # When dead this will hit enter until we exit back to lobby
                self.html_element.send_keys(Keys.RETURN)
                return True
            return False
        except selenium.common.exceptions.StaleElementReferenceException:
            # Hitting this error means we're in the lobby again
            # Flag that we need to re-enter game
            self.dead_state = True
            return True

    def main(self):
        """Log in and run main game loop"""
        self.browser.get(self.login_info['server'])
        self.login()
        self.enter_game()
        # Main gameplay loop
        while True:
            # Check if the player died, restart the game if so
            if self.dead_state:
                self.enter_game()
                self.dead_state = False
                state = FindDownStaircase(self.browser, self.navigate)
            # Record the current turn, so we know when the it goes up later
            # If this no longer exists we are dead and need to re-enter the game
            try:
                turncount = (self.browser.find_element_by_id('stats_time').
                             get_attribute('innerHTML'))
            except selenium.common.exceptions.NoSuchElementException:
                self.dead_state = True
                continue
            num_enemies = self.check_threats()
            last_message = self.get_last_message()
            # Enter commands for the player
            if num_enemies > 0:
                # Auto fight when enemies are around
                # Will need to be replaced with my own pathfinding someday
                self.html_element.send_keys(Keys.TAB)
            elif ('There is a lethal amount of poison in your body!'
                  in last_message):
                # We have already been poisoned to death, just wait to die
                # I'll figure out item use later
                self.html_element.send_keys('.')
            elif not self.get_player_health_full():
                # Rest if we are hurt
                self.html_element.send_keys('5')
            elif 'explor' in last_message:
                self.state.Update()
            else:
                # Explore if nothing else is going on
                self.html_element.send_keys('o')

            self.wait_for_turn_advancement(turncount)


if __name__ == '__main__':
    DerpyAi().main()
