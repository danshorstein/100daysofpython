from logbook import Logger, StreamHandler
from logbook.notifiers import PushoverHandler
import sys

StreamHandler(sys.stdout).push_application()
# PushoverHandler(application_name='Dog Bark', apikey='aydx41drtskjxbj14egvyunchi64ka', userkey='uofggy6u4pw9exq3ikmmwe5iwfarxm').push_application()
log = Logger('Logbook')
log.info('Hello world!')
log.error('oh shit!!!')
