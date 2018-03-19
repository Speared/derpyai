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
# Note that these glyphs arn't all accurate to the actual game
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
    (255, 255, 255): ("player", "@", 1),
    (17, 68, 85): ("shallow water", "~", 5),
    (0, 17, 34): ("deep water", "`", 5)
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


def _get_a_node(coordinates, parent):
    pixels = minimap.load()
    feature = MAP_FEATURES[pixels[coordinates]]
    travel_cost = feature[FEATURE_ASCORE]
    # If travel cost is -1 this isn't a valid path tile
    # Just return nothing
    if travel_cost == -1:
        return None
    neighbors = _get_neighbors(coordinates)
    new_node = {'travel_cost': travel_cost, 'best_path': [], 'best_cost': 0,
                'open_neighbors': neighbors, 'coordinates': coordinates}
    if parent is not None:
        best_path = list(parent['best_path'])
        best_path.append(coordinates)
        new_node['best_path'] = best_path
        best_cost = parent['best_cost'] + travel_cost
        new_node['best_cost'] = best_cost
    return new_node


def _get_path(start, goal):
    startingNode = _get_a_node(start, None)
    openNodes = [startingNode]
    # key = coordinate, value = node
    checkedNodes = {}
    while len(openNodes) > 0:
        # First get the lowest-cost node
        cheapest_node = None
        cheapest_value = 0
        for node in openNodes:
            if cheapest_node is None:
                cheapest_node = node
                cheapest_value = node['best_cost']
            else:
                if node['best_cost'] < cheapest_value:
                    cheapest_value = node['best_cost']
                    cheapest_node = node
        # Now check each neighbor of this node, work with the closest open one
        # No unchecked neighbors left means we can remove
        #   this from the open list
        if len(cheapest_node['open_neighbors']) == 0:
            openNodes.remove(cheapest_node)
            continue
        closest_neighbor = None
        closest_dist = 0
        for neighbor in cheapest_node['open_neighbors']:
            if closest_neighbor is None:
                closest_neighbor = neighbor
                closest_dist = _get_squared_distance(neighbor[0], goal)
            else:
                dist = _get_squared_distance(neighbor[0], goal)
                if dist < closest_dist:
                    closest_neighbor = neighbor
                    closest_dist = dist
        # Pop this neighbor off the open stack to prevent re-checking
        cheapest_node['open_neighbors'].remove(closest_neighbor)
        new_node = _get_a_node(closest_neighbor[0], cheapest_node)
        # Nodes will be none for invalid tiles (deep water, walls)
        if new_node is None:
            continue
        # If our newest node is at the goal we're finished
        if new_node['coordinates'] == goal:
            return new_node['best_path']
        # Check if this neighbor's coordinates are already in the dict
        coordinates = new_node['coordinates']
        if coordinates not in checkedNodes:
            checkedNodes[coordinates] = new_node
            openNodes.append(new_node)
        else:
            # If this node already exists replace it
            #   if the new path is better
            if new_node['best_cost'] < checkedNodes[coordinates]['best_cost']:
                checkedNodes[coordinates] = new_node
                openNodes.append(new_node)
    # If we made it here we ran out of paths to try
    return None


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


def _debug_print_path(path):
    pixels = minimap.load()
    print len(path)
    for coordinate in path:
        print coordinate
        pixels[coordinate] = (255, 255, 0)
    width, height = minimap.size
    minimap.resize((width * 4, height * 4)).save('images/debug_path.bmp')


def _tests(browser):
    print "\nget map"
    _get_map(browser)
    print "\nsample frequencies"
    _get_map_frequencies()
    print "\nfind down staircases"
    downstairs = _get_map_feature('>')
    for stairs in downstairs:
        print stairs
    print "\nfind player"
    player = _get_map_feature('@')[0]
    print player
    print "\nfind player's neighbors"
    neighbors = _get_neighbors(player)
    for neighbor in neighbors:
        print neighbor
    print "\nfind a path to a staircase"
    if len(downstairs) > 0:
        path = _get_path(player, downstairs[0])
        if path is not None:
            _debug_print_path(path)
        else:
            print "No path found"


# Finds all the tiles matching a given name/glyph/a* value
def get_map_feature(findme):
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


# Inject code into the web page, download the minimap canvas as
#   a png and save it
def get_map(browser):
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
