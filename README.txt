Currently takes a bit of setup on the crawl server to work right
	server is hard coded to http://crawl.berotato.org:8080/#lobby at the moment
	you'll need to have a username/password on this server, and enter them into the login.txt file
	set the rc file for the latest version of crawl to have the settings in rc.txt

Run derpyay.py to run the bot. Note that this project is in its early stages
and there's a lot of situations that will get it stuck (y/n prompts, map tiles
it hasn't seen before, enemies it can't reach with just mashing the autofight button,
crashing from a bug in the minimap code while finding staircases). For anything other 
than the bot crashing giving it some maual help will usually put it back on track. 
	
Project takes Python 2.7, Selenium, ChromeDriver and PIL to run
	https://www.python.org/download/releases/2.7/
	https://pypi.python.org/pypi/selenium
	https://sites.google.com/a/chromium.org/chromedriver/downloads
	http://www.pythonware.com/products/pil/
	
