import json

import requests

url = 'https://api.pushover.net/1/messages.json'

with open('/home/pi/Python/projects/100daysofpython/Days_2_&_3/services/secrets.json') as fin:
    secrets = json.load(fin)

def send_push(time_barked, count):
    message = 'BARK BARK LET ME IN!!!! Barked at {}, total of {} barks'.format(time_barked, count)
    title = 'LET THE DOG IN!!'
    body = {'token': secrets['token'],
        'user': secrets['user'],
        'message': message,
       'title': title}
    
    r = requests.post(url, body)

if __name__ == '__main__':
    send_push()
