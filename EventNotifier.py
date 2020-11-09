from discord_webhook import DiscordWebhook
import mysql.connector
import sys
import argparse
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dateutil.parser import parse


parser = argparse.ArgumentParser(description='Take in secrets for this script.')
parser.add_argument('--channelid',  help='a channel id for the accouncements' )
parser.add_argument('--dbpassword',  help='password for the db')
# parser.add_argument('--sum', dest='accumulate', action='store_const',
#                    const=sum, default=max,
#                    help='sum the integers (default: find the max)')
args = parser.parse_args()

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Set up discord
uri = "https://discordapp.com/api/webhooks/{}".format(args.channelid)

# connect to the db
try:
    print("Connecting to database.")
    conn = mysql.connector.connect(
        user="app0005",
        password=args.dbpassword,
        host="192.168.1.101",
        port=3306,
        database="csg_automations"
    )

except mysql.connector.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

print("Successful connection to database.")

cursor = conn.cursor()

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('calendar', 'v3', credentials=creds)

# Call the Calendar API
now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
print('Getting the upcoming 10 events')
events_result = service.events().list(calendarId='iu.edu_ghkkngbm6i2qadsla4ktnpgi50@group.calendar.google.com', timeMin=now,
                                    maxResults=10, singleEvents=True,
                                    orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    eventid = event['id']
    eventTime = parse(event['start']['dateTime'])
    event30 = eventTime - datetime.timedelta(minutes=30)
    event3 = eventTime - datetime.timedelta(days=3)

    webhook = DiscordWebhook(url=uri,
                             content=f"@everyone Hey reminder bot here,\n CSG will be hosting '{event['summary']}' in 3 days on the {eventTime.day} at {eventTime.now().strftime('%H:%M')}."
                                     f"We hope to see everyone their!\n"
                                     f"------------------------------\n"
                                     f"Details: {event['description']}")
    response = webhook.execute()

    cursor.execute(f"SELECT * FROM csg_automations.eventNotification where eventID = '{eventid}'")
    data = cursor.fetchone()
    if data is None:
        cursor.execute(f"INSERT INTO `csg_automations`.`eventNotification` (`eventId`,`logged`) VALUES ('{eventid}','{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}');")
        conn.commit()


    # send an alert for 3 days before
    if data[1] == 0 and (0 < now - event3 < 15):
        # update db
        cursor.execute(f"UPDATE `csg_automations`.`eventNotification` SET `threeday` = 0 WHERE `eventId` = {eventid};")
        conn.commit()
        # send alert
        webhook = DiscordWebhook(url=uri, content=f"@everyone Hey reminder bot here,\n CSG will be hosting {event['summary']} in 3 days on the {eventTime.day} at {eventTime.time}."
                                                  f"We hope to see everyone their!\n"
                                                  f"------------------------------"
                                                  f"Details: {event['description']}")
        response = webhook.execute()


    # send an alert for 30 minutes before
    if data[2] == 0 and (0 < now - event30 < 15):
        # update db
        cursor.execute(f"UPDATE `csg_automations`.`eventNotification` SET `thirtyminutes` = 0 WHERE `eventId` = {eventid};")
        conn.commit()
        # send alert
        webhook = DiscordWebhook(url=uri,
                                 content=f"@everyone Hey reminder bot here,\n CSG will be hosting {event['summary']} in 30 minutes on the {eventTime.day} at {eventTime.time}."
                                         f"We hope to see everyone their!\n"
                                         f"------------------------------"
                                         f"Details: {event['description']}")
        response = webhook.execute()

    # start = event['start'].get('dateTime', event['start'].get('date'))
    # print(start, event['summary'])

#webhook = DiscordWebhook(url=uri, content='CSG Website was successfully deployed. :white_check_mark: ')

