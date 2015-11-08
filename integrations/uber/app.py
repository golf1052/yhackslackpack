from __future__ import absolute_import

import json
import os
from urlparse import urlparse
import pika

from flask import Flask, render_template, request, redirect, session
from flask_sslify import SSLify
from rauth import OAuth2Service
import requests
import string
import db

requests_session = requests.Session()


with open('config.json') as f:
    config = json.load(f)

rabbit_connection = None
channel = None


def set_up_rabbit():
    global rabbit_connection
    global channel
    rabbit_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = rabbit_connection.channel()

def wait_for_response():
    print "Waiting for response from slack "
    channel.basic_consume(callback, queue="uber", no_ack=True, consumer_tag=queue)
    channel.start_consuming()

# This is what you do when you get back a response
def callback(ch, method, properties, body):
    channel.stop_consuming()
    params = {
        'message': body,
    }
    signup(body)

#here "message" is our standard JSON blob of ID/message
def send_slack_message(message):
    channel.queue_declare(queue="input", passive=True)
    channel.basic_publish(exchange='',routing_key=queue,body=message)
    print "Sending message to service for user "
    print "\nMessage: " + message

def parse_inbound_message(message):
    json_message = json.loads(message)
    print json_message
    user_message = str(json_message['message'])
    print user_message
    if "time" in user_message:
        send_slack_message(time())
    if "history" in user_message:
        send_slack_message(history())
    #etc etc for all of these



def generate_oauth_service():
    """Prepare the OAuth2Service that is used to make requests later."""
    return OAuth2Service(
        client_id=os.environ.get('UBER_CLIENT_ID'),
        client_secret=os.environ.get('UBER_CLIENT_SECRET'),
        name=config.get('name'),
        authorize_url=config.get('authorize_url'),
        access_token_url=config.get('access_token_url'),
        base_url=config.get('base_url'),
    )


def generate_ride_headers(token):
    """Generate the header object that is used to make api requests."""
    return {
        'Authorization': 'Bearer %s' % token,
        'Content-Type': 'application/json',
    }


def health():
    """Check the status of this application."""
    return ';-)'



def signup(message):
    """The first step in the three-legged OAuth handshake.

    You should navigate here first. It will redirect to login.uber.com.
    """
    # TODO: check for token (match user object on slack ID)
    # if token, check token works, if not, generate new token as below and put it in the database.
    client = db.get_connection()
    # json
    user_uber_data = client.yhackslackpack.users.find_one({"_id": "U03FQDYTM"})
    if user_uber_data["access_token"] != "":
        print user_uber_data["access_token"]
        # already authed, parse message
        return parse(request.args.get("message"))
    params = {
        'response_type': 'code',
        'redirect_uri': get_redirect_uri(request),
        'scope': ' '.join(config.get('scope')),
    }
    url = generate_oauth_service().get_authorize_url(**params)
    return redirect(url)

def surge_confirm():
    #confirm this is correct
    surge_confirm_id = request.args.get('surge_confirmation_id')

def submit():
    """The other two steps in the three-legged Oauth handshake.

    Your redirect uri will redirect you here, where you will exchange
    a code that can be used to obtain an access token for the logged-in use.
    """
    params = {
        'redirect_uri': get_redirect_uri(request),
        'code': request.args.get('code'),
        'grant_type': 'authorization_code'
    }
    response = app.requests_session.post(
        config.get('access_token_url'),
        auth=(
            os.environ.get('UBER_CLIENT_ID'),
            os.environ.get('UBER_CLIENT_SECRET')
        ),
        data=params,
    )

    session['access_token'] = response.json().get('access_token')
    #send to mongo

    return render_template(
        'success.html',
        token=response.json().get('access_token')
    )

def demo():
    """Demo.html is a template that calls the other routes in this example."""
    return render_template('demo.html', token=session.get('access_token'))


def products():
    """Example call to the products endpoint.

    Returns all the products currently available in New Haven.
    """
    url = config.get('base_uber_url') + 'products'
    params = {
        'latitude': config.get('start_latitude'),
        'longitude': config.get('start_longitude'),
    }

    response = app.requests_session.get(
        url,
        headers=generate_ride_headers(session.get('access_token')),
        params=params,
    )

    if response.status_code != 200:
        return 'There was an error', response.status_code
    return response.text


def ridereq():
    """
    DO NOT USE THE BASE UBER URL OR I GET CHARGED MONEY

    Make a sample ride request. Needs start and end lat/lon
    and the unique Product ID of the Uber service for your city
    """
    url = config.get('sandbox_uber_base_url_v1') + 'requests'
    params = {
        "product_id": "02d5b168-49e2-41a4-a34b-590ea6f49909",
        "start_latitude": 41.313248,
        "start_longitude": -72.931547,
        "end_latitude": 41.297534,
        "end_longitude": -72.926922
    }

    response = app.requests_session.post(
        url,
        headers=generate_ride_headers(session.get('access_token')),
        data='{"start_latitude":"41.3132481","start_longitude":"-72.9315478","end_latitude":"41.297534","end_longitude":"-72.926922","product_id":"02d5b168-49e2-41a4-a34b-590ea6f49909"}',
    )

    if response.status_code != 200:
        print response.json()
    if response.status_code == 409:
        #response.meta.href... send the user here.
        #after that, surge_confirm will be called if the user agrees
        #return "You need to go to " + response.meta.href
        print "409 error"
    return response.text


def time():
    """
    Returns the time estimates from the given lat/lng given below.
    """
    url = config.get('base_uber_url') + 'estimates/time'
    params = {
        'start_latitude': config.get('start_latitude'),
        'start_longitude': config.get('start_longitude'),
    }

    response = app.requests_session.get(
        url,
        headers=generate_ride_headers(session.get('access_token')),
        params=params,
    )

    if response.status_code != 200:
        return 'There was an error', response.status_code
    return response.text

def price():
    """Example call to the price estimates endpoint.

    Returns the time estimates from the given lat/lng given below.
    """
    url = config.get('base_uber_url') + 'estimates/price'
    params = {
        'start_latitude': config.get('start_latitude'),
        'start_longitude': config.get('start_longitude'),
        'end_latitude': config.get('end_latitude'),
        'end_longitude': config.get('end_longitude'),
    }

    response = app.requests_session.get(
        url,
        headers=generate_ride_headers(session.get('access_token')),
        params=params,
    )

    if response.status_code != 200:
        return 'There was an error', response.status_code
    return response.text

def history():
    """Return the last 5 trips made by the logged in user."""
    url = config.get('base_uber_url_v1_1') + 'history'
    params = {
        'offset': 0,
        'limit': 5,
    }

    response = requests_session.get(
        url,
        headers=generate_ride_headers(session.get('access_token')),
        params=params,
    )

    if response.status_code != 200:
        return 'There was an error', response.status_code
    return response.text

def me():
    """Return user information including name, picture and email."""
    url = config.get('base_uber_url') + 'me'
    response = requests_session.get(
        url,
        headers=generate_ride_headers(session.get('access_token')),
    )

    if response.status_code != 200:
        return 'There was an error', response.status_code
    return response.text


def get_redirect_uri(request):
    """Return OAuth redirect URI."""
    parsed_url = urlparse(request.url)
    if parsed_url.hostname == 'localhost':
        return 'http://{hostname}:{port}/submit'.format(
            hostname=parsed_url.hostname, port=parsed_url.port
        )
    return 'https://{hostname}/submit'.format(hostname=parsed_url.hostname)


def getLatLng(address):
    google_key = os.environ.get("GOOGLE_API_KEY")
    google_url = os.environ.get("APITOOLS_GOOGLE_SERVICEURL") + "/geocode/json"

    address = string.replace(address, " ", "+")

    params = {
        'address': address,
        'key': google_key,
    }

    response = requests_session.get(
        google_url,
        params=params,
    )

    if response.status_code != 200:
        return "There was an error", response.json()
    response_data = json.loads(response.text)
    latlng = response_data["results"][0]["geometry"]["location"]

    return latlng

if __name__ == '__main__':
    set_up_rabbit()
    wait_for_response()
