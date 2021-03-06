# Import built-in modules
import base64
from collections import defaultdict
import os
import tempfile
import time

# Import third-party modules
from PIL import Image

# Import local modules
from setup_tests import SetupTests # No longer used


class Navigate(object):

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
        (17, 68, 85): ("shallow water", "w", 5),
        (0, 17, 34): ("deep water", "W", -1),
        (170, 102, 68): ("trap", "~", 50),
        (68, 102, 51): ("plant", "p", 25),
        (85, 34, 17): ("lava", "l", -1)
    }

    #_minimap = None
    #_player_location = (0, 0)

    # Returns every adjacent map feature
    # Return values in list: ( (coordinates), (map_features))
    def _get_neighbors(self, coordinate):
        pixels = _minimap.load()
        width, height = _minimap.size
        neighbors = []
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                # Ignore our own tile
                if x == y == 0:
                    continue
                # Also ignore tiles that are off the map
                if (coordinate[0] + x <= 0 or coordinate[0] + x >= width or
                        coordinate[1] + y <= 0 or coordinate[1] + y >= height):
                    continue
                neighbor_coordinate = (coordinate[0] + x, coordinate[1] + y)
                neighbor = (neighbor_coordinate,
                            self.MAP_FEATURES[pixels[neighbor_coordinate]])
                neighbors.append(neighbor)
        return neighbors

    def _get_squared_distance(self, pos1, pos2):
        a_squared = (pos2[0] - pos1[0]) * (pos2[0] - pos1[0])
        b_squared = (pos2[1] - pos1[1]) * (pos2[1] - pos1[1])
        return a_squared + b_squared

    def _get_a_node(self, coordinates, parent):
        pixels = _minimap.load()
        feature = self.MAP_FEATURES[pixels[coordinates]]
        travel_cost = feature[self.FEATURE_ASCORE]
        # If travel cost is -1 this isn't a valid path tile
        # Just return nothing
        if travel_cost == -1:
            return None
        neighbors = self._get_neighbors(coordinates)
        new_node = {
                   'travel_cost': travel_cost, 'best_path': [], 'best_cost': 0,
                   'open_neighbors': neighbors, 'coordinates': coordinates}
        if parent is not None:
            best_path = list(parent['best_path'])
            best_path.append(coordinates)
            new_node['best_path'] = best_path
            best_cost = parent['best_cost'] + travel_cost
            new_node['best_cost'] = best_cost
        return new_node

    # Get the rgb values of every tile on the
    #   _minimap and how often they occur
    #
    # Should make it easier for me to work out
    #   which rgb value = which map feature
    def _get_map_frequencies(self):
        pixels = _minimap.load()
        width, height = _minimap.size
        color_dict = defaultdict(int)
        print "getting frequencies"
        for x in range(width):
            for y in range(height):
                color_dict[pixels[x, y]] += 1
        for rgb, frequency in color_dict.iteritems():
            print rgb, '\t', frequency

    def _debug_print_path(self, path):
        pixels = _minimap.load()
        print len(path)
        for coordinate in path:
            print coordinate
            pixels[coordinate] = (255, 255, 0)
        width, height = _minimap.size
        _minimap.resize((width * 4, height * 4)).save(
            os.path.join(self.image_folder, 'debug_path.bmp')
        )
        # Undo changes to the map
        self.get_map()
        
    def _debug_print_map(self, filename):
        width, height = _minimap.size
        _minimap.resize((width * 4, height * 4)).save(filename)
        # Undo changes to the map
        self.get_map()

    def get_player_location(self):
        # Search for the player, starting with the tile they were in
        #   last time we checked, then tiles adjactent to their last position,
        #   then finally just search the whole map
        #global player_location
        pixels = _minimap.load()
        player = (255, 255, 255)
        # If the player hasn't moved no need to update anything
        if pixels[self.player_location] == player:
            return self.player_location
        neighbors = self._get_neighbors(self.player_location)
        for neighbor in neighbors:
            # neighbor[0] is the coordinates
            if pixels[neighbor[0]] == player:
                self.player_location = neighbor[0]
                return self.player_location
        self.player_location = self.get_map_feature('@')[0]
        return self.player_location

    # Finds all the tiles matching a given name/glyph/a* value
    def get_map_feature(self, findme):
        return_coordinates = []
        pixels = _minimap.load()
        width, height = _minimap.size
        for x in range(width):
            for y in range(height):
                try:
                    if findme in self.MAP_FEATURES[pixels[x, y]]:
                        return_coordinates.append((x, y))
                except KeyError:
                    print "unknown map feature rgb", pixels[x, y]
        return return_coordinates

    # Inject code into the web page,
    #   download the _minimap canvas as a png and save it
    #
    # Needs to be called once per turn for accurate map info
    def get_map(self):
        # Read the _minimap as a png
        inject_script = open('read_minimap_inject.js', 'r').read()
        global _minimap
        _minimap = self.browser.execute_script(inject_script)
        _minimap = base64.b64decode(_minimap)
        # TODO: could probably skip these steps and convert
        #   the png in memory directly into an image
        minimap_path = os.path.join(self.image_folder, '_minimap.png')
        with open(minimap_path, 'wb') as f:
            f.write(_minimap)
        # Open the new png as a PIL Image
        _minimap = Image.open(minimap_path).convert("RGB")
        # Get the tilesize of the _minimap, then scale
        #   down the map so there's no wasted pixels
        inject_script = open('get_minimap_tile_size_inject.js', 'r').read()
        tilesize = self.browser.execute_script(inject_script)
        width, height = _minimap.size
        x_tiles = width / tilesize
        y_tiles = height / tilesize
        shrunk_minimap = Image.new("RGB", (x_tiles, y_tiles))
        map_pixels = _minimap.load()
        shrunk_pixles = shrunk_minimap.load()
        for x in range(x_tiles):
            for y in range(y_tiles):
                shrunk_pixles[(x, y)] = map_pixels[(x * tilesize, y * tilesize)]
        _minimap = shrunk_minimap
        _minimap.save(os.path.join(self.image_folder, 'debug_map.bmp'))

    def get_path(self, start, goal):
        startingNode = self._get_a_node(start, None)
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
            # Now check each neighbor of this node, work with the
            #   closest open one
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
                    closest_dist = self._get_squared_distance(neighbor[0],
                                                              goal)
                else:
                    dist = self._get_squared_distance(neighbor[0], goal)
                    if dist < closest_dist:
                        closest_neighbor = neighbor
                        closest_dist = dist
            # Pop this neighbor off the open stack to prevent re-checking
            cheapest_node['open_neighbors'].remove(closest_neighbor)
            new_node = self._get_a_node(closest_neighbor[0], cheapest_node)
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
                if (new_node['best_cost'] <
                   checkedNodes[coordinates]['best_cost']):
                    checkedNodes[coordinates] = new_node
                    openNodes.append(new_node)
        # If we made it here we ran out of paths to try
        return None

    def __init__(self, browser):
        self.browser = browser
        self.player_location = (0, 0)
        self.image_folder = tempfile.mkdtemp("derpy_images_")


# Leaving this code in for now, but some of it is likely broken currently, and
# with any luck pathfinding already works well enough that this won't be
# needed.

# if __name__ == "__main__":
#     browser = SetupTests.setup()
#     navigate = Navigate(browser)
#     print "\nget map"
#     navigate.get_map()
#     print "\nsample frequencies"
#     navigate._get_map_frequencies()
#     print "\nfind down staircases"
#     downstairs = navigate.get_map_feature('>')
#     for stairs in downstairs:
#         print stairs
#     print "\nfind player"
#     player = navigate.get_map_feature('@')[0]
#     print player
#     print "\nfind player's neighbors"
#     neighbors = navigate._get_neighbors(player)
#     for neighbor in neighbors:
#         print neighbor
#     print "\nfind a path to a staircase"
#     if len(downstairs) > 0:
#         path = navigate.get_path(player, downstairs[0])
#         if path is not None:
#             navigate._debug_print_path(path)
#         else:
#             print "No path found"
#     turncount = (browser.find_element_by_id('stats_time').
#                 get_attribute('innerHTML'))
#     while True:
#         newturncount = (browser.find_element_by_id('stats_time').
#                         get_attribute('innerHTML'))
#         if turncount != newturncount:
#             turncount = newturncount
#             # Spam the console so I don't forget
#             #   what might be lagging the game
#             print "!!Printing map!!"
#             filename = 'images/minimap_prints/{0}.bmp'.format(turncount)
#             navigate._debug_print_map(filename)
#         time.sleep(0.1)
             
        
