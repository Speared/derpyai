# Reads pixle data of the minimp canvas and tries to convert it into
#   html tags I can read with the python script
# All tags have the class name 'minimap_data' to fetch them
# Tags ID is x/y coordinates, in that order, seperated by commas
# Tags innerHTML is rgb data, also in that order and comma seperated 
import base64
from collections import defaultdict

from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import selenium.common.exceptions

MAP_WIDTH = 80
MAP_HEIGHT = 70

# key = rgb value, value = (name, glyph, a* pathfinding score)
FEATURE_NAME = 0
FEATURE_GLYTH = 1
FEATURE_ASCORE = 2
MAP_FEATURES = {
    (0, 255, 255): ("up stairway", "<", 1),
    (119, 85, 68): ("door", "+", 2),
    (0, 85, 68): ("item", "%", 1),
    (102, 102, 102): ("wall", "0", -1),
    (255, 0, 255): ("down stairway", ">", 1),
    (51, 51, 51): ("floor", ".", 1),
    (0, 0, 0): ("unexplored", " ", 10),
    (255, 255, 255): ("player", "@", 0)
    }

minimap = None

# Returns every adjacent map feature
# Return values in list: ( (coordinates), (map_features)) 
def _get_neighbors(coordinate):
    pixels = minimap.load()
    width, height = minimap.size
    neighbors = []
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            # Ignore our own tile
            if x == y == 0:
                continue
            # Also ignore tiles that are off the map   
            if (coordinate[0] + x < 0 or coordinate[0] + x > width or
                   coordinate[1] + y < 0 or coordinate[1] + y > height):
                continue
            neighbor_coordinate = (coordinate[0] + x, coordinate[1] + y)
            neighbor = (neighbor_coordinate,
                        MAP_FEATURES[pixels[neighbor_coordinate]])
            neighbors.append(neighbor)
    return neighbors



def _get_squared_distance(pos1, pos2):
    a_squared = (pos2[0] - pos1[0]) * (pos2[0] - pos1[0])
    b_squared = (pos2[1] - pos1[1]) * (pos2[1] - pos1[1])
    return a_squared + b_squared


def _get_a_node(coordinates):
    pixels = minimap.load()
    feature = MAP_FEATURES[pixels[coordinates]]
    travel_cost = feature[FEATURE_ASCORE]
    return {'travel_cost': travel_cost, 'best_path': [], 'best_cost': [],
            'open_neighbors': [], 'checked_neighbors': [],
            'coordinates': coordinates}

            
def _get_path(start, goal):
    startingNode = _get_a_node(start)
    openNodes = [start]
    checkedNodes = []
    
    while len(openNodes) > 0:
        # First get the closest node to the goal
        closest_node = None
        closest_dist = 0
        for node in openNodes:
            if closest_node = None:
                closest_node = node
                closest_dist = _get_squared_distance(node[coordinates], goal)
            else:
                dist = _get_squared_distance(node[coordinates], goal)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_node = node
        # Now check each neighbor of this node and add them to the path 
                
            
    

# Finds all the tiles matching a given name/glyph/a* value
def _get_map_feature(findme):
    return_coordinates = []
    pixels = minimap.load()
    width, height = minimap.size
    for x in range(width):
        for y in range(height):
            try:
                if findme in MAP_FEATURES[pixels[x, y]]:
                    return_coordinates.append((x, y))
            except KeyError:
                print "unknown map feature rgb", pixels[x, y]
    return return_coordinates


# Get the rgb values of every tile on the minimap and how often they
#   occur
# Should make it easier for me to work out which rgb value = which map
#   feature
def _get_map_frequencies():
    pixels = minimap.load()
    width, height = minimap.size
    color_dict = defaultdict(int)
    print "getting frequencies"
    for x in range(width):
        for y in range(height):
            color_dict[pixels[x, y]] += 1
    for rgb, frequency in color_dict.iteritems():
        print rgb, '\t', frequency


# Inject code into the web page, download the minimap canvas as
#   a png and save it
def _get_map(browser):
    print "getting map"
    # Read the minimap as a png
    inject_script = open('read_minimap_inject.js', 'r').read()
    global minimap
    minimap = browser.execute_script(inject_script)
    minimap = base64.b64decode(minimap)
    # TODO: could probably skip these steps and convert the png in 
    #   memory directly into an image
    with open(r"images/minimap.png", 'wb') as f:
        f.write(minimap)
    # Open the new png as a PIL Image 
    minimap = Image.open("images/minimap.png").convert("RGB")
    # Get the tilesize of the minimap, then scale down the map so
    #   there's no wasted pixles 
    inject_script = open('get_minimap_tile_size_inject.js', 'r').read()
    tilesize = browser.execute_script(inject_script)
    print "minimap tilesize:", tilesize
    print "map height: {0} map width: {1}".format(minimap.size[1],
                                                  minimap.size[0])
    resize_percentage = minimap.size[1] / float(MAP_HEIGHT) 
    new_width = int(minimap.size[0] / resize_percentage)
    minimap = minimap.resize((new_width, MAP_HEIGHT))
    print "new map height: {0} new map width: {1}".format(minimap.size[1],
                                                          minimap.size[0])
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

    print "get map"
    get_map(browser)
    #print "sample frequencies"
    #_get_map_frequencies()
    print "find down staircases"
    downstairs = _get_map_feature('>')
    for stairs in downstairs:
        print stairs
    print "find player"
    player = _get_map_feature('@')[0]
    print player
    print "find player's neighbors"
    neighbors = _get_neighbors(player)
    for neighbor in neighbors:
        print neighbor
