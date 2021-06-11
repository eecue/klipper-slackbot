# klipper-slackbot
This is a basic slackbot for getting status from Klipper via Moonraker.  It uses the Slackbot Sockets fucntionality so you can run it directly on your Raspberry Pi without needing to expose it to the internet. It looks for the word status in any channel that it belongs to and then grabs the webcam image, uploads it, and adds some info about your printer.  

[img screenshot.png]

You will need to install slack_bolt, requests and dotenv.  Run the bot as follows: python app.py