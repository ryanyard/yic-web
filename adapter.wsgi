import sys, os, bottle

sys.path = ['/var/www/html/restapi'] + sys.path
os.chdir(os.path.dirname(__file__))

import restapi
application = bottle.default_app()
