# Reads pixle data of the minimp canvas and tries to convert it into
#   html tags I can read with the python script
# All tags have the class name 'minimap_data' to fetch them
# Tags ID is x/y coordinates, in that order, seperated by commas
# Tags innerHTML is rgb data, also in that order and comma seperated 
import base64

from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

MAP_WIDTH = 80
MAP_HEIGHT = 70

minimap = None
    
def get_map(browser):
    print "getting map"
    # Read the minimap as a png
    inject_script = open('read_minimap_inject.js', 'r').read()
    minimap = browser.execute_script(inject_script)
    minimap = base64.b64decode(minimap)
    # TODO: could probably skip these steps and convert the png in 
    #   memory directly into an image
    print minimap
    with open(r"images/minimap.png", 'wb') as f:
        f.write(minimap)
    # Open the new png as a PIL Image 
    minimap = Image.open("images/minimap.png").convert("RGB")
    minimap.save('minimap.bmp')
    
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
    get_map(browser)
