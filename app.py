import os
import requests 
import logging
import time
from dotenv import load_dotenv
from requests.api import get
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Initializes your app with your bot token and signing secret
app = App(token=os.environ["SLACK_BOT_TOKEN"])

moonraker_url = os.environ["MOONRAKER_URL"]
webcam_image_url = os.environ["WEBCAM_IMAGE_URL"]

def download_image():
  response = requests.get(webcam_image_url)
  filename = "printer_image.jpg"
  file = open(filename, "wb")
  file.write(response.content)
  file.close()
  return filename


def get_moonraker_status():
  response = requests.get(f"{moonraker_url}/printer/objects/query?gcode_move&toolhead&extruder=target,temperature&display_status&mcu&heaters&system_stats&fan&extruder&heater_bed&print_stats")
  json_data = response.json()["result"]["status"]
  json_data["metadata"] = get_gcode_metadata(json_data['print_stats']['filename'])
  #logger.error(json_data)
  return json_data


def get_gcode_metadata(gcode_filename):
  response = requests.get(f"{moonraker_url}/server/database/item?namespace=gcode_metadata")
  json_data = response.json()["result"]["value"][gcode_filename]
  # logger.error(json_data)
  return json_data

# @app.command("/klipper")
# def repeat_text(ack, say, command):
#     # Acknowledge command request
#     ack()
#     say(f"{command['text']}")

@app.message("status")
def show_printer_status(client, message, say):
 
    client.reactions_add(
        name="traffic_light",
        channel=message["channel"],
        timestamp=message["ts"]
    )

 
    fn = download_image()
    file_name = f"./{fn}"
    response = client.files_upload(
        initial_comment="File upload complete :up:  gathering other data :clock2: ",
        channels=message["channel"],
        file=file_name,
    )

    ts = response['file']['shares']['public'][message['channel']][0]['ts']

    pd = get_moonraker_status()
    print_time = time.strftime('%-H:%M', time.gmtime(pd["print_stats"]["print_duration"]))
    actual_time = time.strftime('%-H:%M', time.gmtime(pd["print_stats"]["total_duration"]))
    total_time = time.strftime('%-H:%M', time.gmtime(pd["metadata"]["estimated_time"]))
    remaining_time = time.strftime('%-H:%M', time.gmtime(pd["metadata"]["estimated_time"] - pd["print_stats"]["print_duration"]))
    percent_complete = int(100 * pd['display_status']['progress'])

    block_message = [{
        "type": "header",
        "text": {
          "type": "plain_text",
          "text": f"{pd['print_stats']['filename']} - {pd['print_stats']['state']} - {percent_complete}% - {remaining_time} remaining",
          "emoji": True
        }
      },
      {
        "type": "context",
        "elements": [
          {
            "type": "plain_text",
            "text": f"Voron 2.4 - Print Time: {print_time} - Total Time: {actual_time}",
            "emoji": True
          }
        ]
      },
      {
        "type": "context",
        "elements": [
          {
            "type": "image",
            "image_url": "https://avatars.githubusercontent.com/u/44981431?s=200&v=4",
            "alt_text": "Voron"
          },
          {
            "type": "mrkdwn",
            "text": f"*Printbot* has an update for you <@{message['user']}>!"
          }
        ]
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": f":bed::thermometer: {round(pd['heater_bed']['temperature'])}?? ({int(100 * pd['heater_bed']['power'])}%)\n\
:syringe::thermometer: {round(pd['extruder']['temperature'])}?? ({int(100 * pd['extruder']['power'])}%)\n\
:round_pushpin:   x:{round(pd['toolhead']['position'][0])} y:{round(pd['toolhead']['position'][1])} z:{round(pd['toolhead']['position'][2],2)}mm\n\
:cyclone:   {int(100*pd['fan']['speed'])}%\n\
:clock3:   {print_time} / {total_time}\n\
:thread:  {round(pd['print_stats']['filament_used']/1000)}m / {round(pd['metadata']['filament_total']/1000)}m        "
        }
      }
    ]


    action_message = [
      {
			"type": "actions",
			"elements": [
				{
					"type": "button",
          "action_id": "printer_action_pause",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": ":double_vertical_bar: Pause"
					},
					"style": "primary",
				},
				{
					"type": "button",
          "action_id": "printer_action_resume",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": ":black_right_pointing_triangle_with_double_vertical_bar: Resume"
					},
					"style": "primary",
				},
				{
					"type": "button",
          "action_id": "printer_action_cancel",
          "text": {
						"type": "plain_text",
						"emoji": True,
						"text": ":x: Cancel"
					}, 
          "confirm": {
            "title": {
                "type": "plain_text",
                "text": "Are you sure?"
            },
            "text": {
                "type": "mrkdwn",
                "text": "This will *cancel the print*!"
            },
            "confirm": {
                "type": "plain_text",
                "text": "CANCEL PRINT"
            },
            "deny": {
                "type": "plain_text",
                "text": "Stop, I've changed my mind!"
            },
          },   
        },
				{
					"type": "button",
          "action_id": "printer_action_stop",
          "text": {
						"type": "plain_text",
						"emoji": True,
						"text": ":octagonal_sign: Emergency STOP"
					}, 
          "confirm": {
            "title": {
                "type": "plain_text",
                "text": "Are you sure?"
            },
            "text": {
                "type": "mrkdwn",
                "text": "This will *halt the printer*!"
            },
            "confirm": {
                "type": "plain_text",
                "text": "EMERGENCY STOP PRINT"
            },
            "deny": {
                "type": "plain_text",
                "text": "Stop, I've changed my mind!"
            },
          },   
					"style": "danger",
					"value": "cancel_print"
				}
			]
		}
    ]




    client.chat_postMessage(
        channel=message["channel"],
        # thread_ts=message_ts,
        text="Printer actions",
        blocks=action_message
        # You could also use a blocks[] array to send richer content
    )

    response = client.chat_update(
      channel=message["channel"],
      text=f"Hey there <@{message['user']}>!",
      ts=ts,
      blocks=block_message
    )

    client.reactions_add(
        name="white_check_mark",
        channel=message["channel"],
        timestamp=message["ts"]
    )

    client.reactions_remove(
        name="traffic_light",
        channel=message["channel"],
        timestamp=message["ts"]
    )



@app.action("printer_action_pause")
def approve_request(ack, say):
    # Acknowledge action request
    ack()
    requests.post(f"{moonraker_url}/printer/print/pause")
    say(":printer: :double_vertical_bar:  Print Paused")

@app.action("printer_action_resume")
def approve_request(ack, say):
    # Acknowledge action request
    ack()
    requests.post(f"{moonraker_url}/printer/print/resume")
    say(":printer: :black_right_pointing_triangle_with_double_vertical_bar: Print Resumed")

@app.action("printer_action_cancel")
def approve_request(ack, say):
    # Acknowledge action request
    ack()
    requests.post(f"{moonraker_url}/printer/print/cancel")
    say(":printer: :x:   Print Cancelled")

@app.action("printer_action_stop")
def approve_request(ack, say):
    # Acknowledge action request
    ack()
    requests.post(f"{moonraker_url}/printer/emergency_stop")
    say(":printer: :octagonal_sign:   Print Stopped")




@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


@app.message(":wave:")
def say_hello(message, say):
    user = message['user']
    say(f"Hi there, <@{user}>!")

@app.event("app_home_opened")
def update_home_tab(client, event, logger):
  try:
    # views.publish is the method that your app uses to push a view to the Home tab
    client.views_publish(
      # the user that opened your app's app home
      user_id=event["user"],
      # the view object that appears in the app home
      view={
        "type": "home",
        "callback_id": "home_view",

        # body of the view
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Welcome to your _App's Home_* :tada:"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app."
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": {
                  "type": "plain_text",
                  "text": "Click me!"
                }
              }
            ]
          }
        ]
      }
    )
  
  except Exception as e:
    logger.error(f"Error publishing home tab: {e}")

@app.action("print_control")
def approve_request(ack, say):
    # Acknowledge action request
    ack()
    say("Request approved ????")



if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
