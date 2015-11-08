import time
import ConfigParser
import pika
import imp
import json
from threading import Thread
from slackclient import SlackClient

PROJECT_ROOT = "../"
channel = None
sc = None
slack_channel = None

def start_pika():
    print 'starting pika'
    connection = pika.SelectConnection(pika.ConnectionParameters(host='localhost'))
    #t = Thread(target=connection.ioloop.start())
    #t.start()

def on_connected(connection):
    connection.channel(on_channel_open)

def on_channel_open(new_channel):
    global channel
    channel = new_channel
    channel.queue_declare(queue='input',callback=on_queue_declared)

def on_queue_declared(frame):
    print "Waiting for response from user " + queue
    channel.basic_consume(received_message, queue=queue, no_ack=True, consumer_tag=queue)

def received_message(ch, method, properties, body):
    print "Bot Received %r" % (body,)
    body_dict = json.loads(body)
    ims = sc.api_call('im.list')
    chan = _get_user_im_channel(body_dict['user'], ims[0]['ims'])
    if (chan != None):
        sc.rtm_send_message(chan, body_dict['message'])

def _get_user_im_channel(user, ims):
    for im in ims:
        if im['user'] == user:
            return im['id']
    return None

#==========================
# COMMUNICATE WITH SERVICES
#=========================
# Sends messages to the service with the format
#
# {
#     "user":""
#     "message":""
# }
#
# It's up to the service to parse the message.
# Bot will wait for a response to post back to slack

def send_message(queue, payload):
    print "Service already running"
    channel.basic_publish(exchange='',routing_key=queue,body=payload)
    print "Sending message to service for user " + queue
    print "\nMessage: " + payload

def start_service(service, user, message):
    print 'Creating queue for ' + service
    channel.queue_declare(queue=service)
    print "Starting service " + service
    service_obj = get_service_module(service)
    payload = {}
    payload['user'] = user
    payload['message'] = message
    t = Thread(target=service_obj.main, args=(json.dumps(payload),))
    t.start()

def get_service_module(service):
    config = ConfigParser.ConfigParser()
    config.read(PROJECT_ROOT + "/modules.ini")
    service_path = PROJECT_ROOT + config.get('Modules', service)
    return imp.load_source('module.name', service_path)

# Process input from slack and either spin up the related service
# or send the message as part of an ongoing exchange
def process(user, message):
    global channel
    # If a queue exists for the process, send it on that queue
    try:
        integration = message.partition(' ')[0]
        channel.queue_declare(queue=integration, passive=True)
        payload = {}
        payload['user'] = user
        payload['message'] = message
        send_message(integration, payload)

    #Service is currently not running. We need to start it. Idk how to MQ
    except pika.exceptions.ChannelClosed:
        channel = connection.channel()
        service = message.partition(' ')[0] #assume the service name is the first thing in the message. Yes its janky. This is a fucking hackathon
        message.strip(service)
        print "Checking message: " + message
        start_service(service, user, message)

def run(apikey):
    global sc, slack_channel
    sc = SlackClient(apikey)
    if sc.rtm_connect():
        global generalID
        generalID = sc.server.channels.find('general').id
        while True:
            response = sc.rtm_read()
            if response != []:
                print response
                if 'type' in response[0] and response[0]['type'] == 'message':
                    # direct messages start with D
                    if (response[0]['channel'][0] == 'D' and response[0]['user'] != 'U0E2LB8C8'):
                        slack_channel = response[0]['channel']
                        t = Thread(target=process, args=(response[0]['user'],response[0]['text']))
                        t.start()
            time.sleep(1)
    else:
        print 'connection failed'


def main():
    start_pika()
    config = ConfigParser.ConfigParser()
    config.read("../credentials.ini")
    token = config.get('Slack', 'apikey')
    run(token)


if __name__ == '__main__':
    main()