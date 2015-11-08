# YHackSlackPack
It rhymes!

## What is it?
The YHackSlackPack is a bunch of integrations for Slack.

### Current Integrations
- Venmo
  - View balance
  - Pay/Charge by username, phone, or email
  - View pending Venmos
  - Complete/reject a pending Venmo
- Tinder
  - View nearby Tinder profiles
  - Swipe left or right on a profile
- Uber (not completed)
  - Order and uber
  - See history
  - Price requests
  - Update in realtime
  
### Potential Integrations
- SMS (using Twilio)
- Dominos (order pizza)
- Twitter (send Tweets)

## How does it work?
There are two fundamental parts. A bot running on Slack waiting for messages and integrations waiting to perform actions on messages.

### Bot
The bot waits for a private message to be sent to it by a user. Once it receives a message the bot will check to see if there is an integration that can respond to the message. If there is one the bot will send the message along with the user ID of the user who sent the message to a queue. The bot also listens on an input queue and once a message comes in from an integration the bot will send that message to the specified Slack user by a private message.

### Integrations
Integrations get started by the bot if they currently are not running. The integration gets passed the message and user ID as an argument. The integration should then process the message and perform an action. Once the integration is done it should send a message back to the input queue so the bot can send the message to Slack. The integration can then quit at this point or it can stay running waiting for more messages from the queue.

Using Venmo as an example the Venmo integration may get "venmo charge $1 for lunch to jeff" from the bot. The integration will look for the Venmo username jeff in the currently authed user's friend's list and then create a Venmo charge of $1 with a note of lunch. Once the charge has been created the Venmo integration sends a confirmation message and quits.