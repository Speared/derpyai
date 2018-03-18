# Reads pixle data of the minimp canvas and tries to convert it into
#   html tags I can read with the python script
# All tags have the class name 'minimap_data' to fetch them
# Tags ID is x/y coordinates, in that order, seperated by commas
# Tags innerHTML is rgb data, also in that order and comma seperated 
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

MAP_WIDTH = 80
MAP_HEIGHT = 70

def print_map(minimap):
    printme = Image.new('RGB', (MAP_WIDTH, MAP_HEIGHT), color=0)
    pixels = printme.load()
    for pixle in minimap:
        coordinate = map(int, pixle.get_attribute('id').split(','))
        color = map(int, pixle.get_attribute('innerHTML').split(','))
        print coordinate, color
        pixels[coordinate[0],coordinate[1]] = (color[0], color[1], color[2])
    printme = printme.resize((MAP_WIDTH * 8, MAP_HEIGHT * 8))
    printme.save('minimap.bmp')

def get_map(browser):
    print "getting map"
    inject_script = open('read_minimap_inject.js', 'r').read()
    browser.execute_script(inject_script)
    minimap = browser.find_elements_by_class_name('minimap_data')
    print_map(minimap)
    
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
