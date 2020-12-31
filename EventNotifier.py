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
parser.add_argument('--channelid', help='a channel id for the accouncements')
parser.add_argument('--dbpassword', help='password for the db')
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
try:
    service = build('calendar', 'v3', credentials=creds)
except:
    e = sys.exc_info()[0]
    print(e)
    exit(1)

# Call the Calendar API
now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
print('fetching the closest 10 events')
events_result = service.events().list(calendarId='iu.edu_ghkkngbm6i2qadsla4ktnpgi50@group.calendar.google.com',
                                      timeMin=now,
                                      maxResults=10, singleEvents=True,
                                      orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    eventid = event['id']
    print(f"Processing {eventid}:'{event['summary']}'")
    epsilon = 30
    now = datetime.datetime.now()
    # Some events are deadlines which we put in as events that last all day.
    # These events will be logged sparely in the db and have a different schedule
    # Deadlines alert at noon on the following schedule:  1 week before, 3 days before, and 1 day before

    # If event['start'] is of date assume it is a deadline
    if list(event['start'].keys())[0] == 'date':
        deadlineTime = parse(event['start']['date'])

        # if deadline exists in db get details otherwise create it
        cursor.execute(f"SELECT * FROM csg_automations.eventNotification where eventID = '{eventid}'")
        data = cursor.fetchone()
        if data is None:
            cursor.execute(
                f"INSERT INTO `csg_automations`.`eventNotification` (`eventId`,`type`) VALUES ('{eventid}', 'deadline' )")
            conn.commit()
            # Get the data that we just entered
            cursor.execute(f"SELECT * FROM csg_automations.eventNotification where eventID = '{eventid}'")
            data = cursor.fetchone()

        # See if the time is within epsilon (15 minutes)
        deadline1w = (deadlineTime - datetime.timedelta(days=7)).replace(hour=12)
        deadline3d = (deadlineTime - datetime.timedelta(days=3)).replace(hour=12)
        deadline1d = (deadlineTime - datetime.timedelta(days=1)).replace(hour=12)
        # deadline1d = (parse(event['end']['date'])).replace(hour=12)

        # 1 week alert
        if data[2] == 0 and (-epsilon < divmod(((now - deadline1w).total_seconds()), 60)[0] < epsilon):
            # update db
            cursor.execute(
                f"UPDATE `csg_automations`.`eventNotification` SET `oneWeek` = 1 WHERE `eventId` = {eventid};")
            conn.commit()
            # send alert
            webhook = DiscordWebhook(url=uri,
                                     content=f"@everyone Hey reminder bot here,\n The CSG has a deadline for "
                                             f"{event['summary']} in 1 week. "
                                             f"Please do not forget to sign up if your interested. \n"
                                             f"------------------------------"
                                             f"Details: {event['description']}")
            response = webhook.execute()
            print(response)

            # Send an email here if you want

        # 3 day alert
        if data[3] == 0 and (-epsilon < divmod(((now - deadline3d).total_seconds()), 60)[0] < epsilon):
            # update db
            cursor.execute(
                f"UPDATE `csg_automations`.`eventNotification` SET `threeDay` = 1 WHERE `eventId` = {eventid};")
            conn.commit()
            # send alert
            webhook = DiscordWebhook(url=uri,
                                     content=f"@everyone Hey reminder bot here,\n The CSG has a deadline for"
                                             f" {event['summary']} in 3 days. "
                                             f"Please do not forget to sign up if your interested. \n"
                                             f"------------------------------"
                                             f"Details: {event['description']}")
            response = webhook.execute()
            print(response)

        # 1 day alert
        if data[4] == 0 and (-epsilon < divmod(((now - deadline1d).total_seconds()), 60)[0] < epsilon):
            # update db
            cursor.execute(
                f"UPDATE `csg_automations`.`eventNotification` SET `oneDay` = 1 WHERE `eventId` = {eventid};")
            conn.commit()
            # send alert
            webhook = DiscordWebhook(url=uri,
                                     content=f"@everyone Hey reminder bot here,\n The CSG has a deadline for"
                                             f" {event['summary']} in 1 days."
                                             f" Please do not forget to sign up if your interested. \n"
                                             f"Tomorrow will be the last day to sign up."
                                             f"------------------------------"
                                             f"Details: {event['description']}")
            response = webhook.execute()
            print(response)

    else:
        # Events alert on the following schedule: 3 days before, 1 day before, 30 minutes before
        eventTime = parse(event['start']['dateTime'])
        event3d = (eventTime - datetime.timedelta(days=3)).replace(tzinfo=None)
        event1d = (eventTime - datetime.timedelta(days=1)).replace(tzinfo=None)
        event30min = (eventTime - datetime.timedelta(minutes=30)).replace(tzinfo=None)

        # if event exists in db get details otherwise create it
        cursor.execute(f"SELECT * FROM csg_automations.eventNotification where eventID = '{eventid}'")
        data = cursor.fetchone()
        if data is None:
            cursor.execute(
                f"INSERT INTO `csg_automations`.`eventNotification` (`eventId`,`type`) VALUES ('{eventid}', 'event' )")
            conn.commit()
            # Get the data that we just entered
            cursor.execute(f"SELECT * FROM csg_automations.eventNotification where eventID = '{eventid}'")
            data = cursor.fetchone()

        # send an alert for 3 days before
        if data[2] == 0 and (-epsilon < divmod(((now - event3d).total_seconds()), 60)[0] < epsilon):
            # update db
            cursor.execute(
                f"UPDATE `csg_automations`.`eventNotification` SET `threeday` = 1 WHERE `eventId` = {eventid}")
            conn.commit()
            # send alert
            webhook = DiscordWebhook(url=uri, content=f"@everyone Hey reminder bot here,\n CSG will be hosting "
                                                      f"{event['summary']} in 3 days"
                                                      f" on the {eventTime.day} at {eventTime.time}."
                                                      f"We hope to see everyone their!\n"
                                                      f"------------------------------"
                                                      f"Details: {event['description']}")
            response = webhook.execute()
            print(response)

        # send an alert for 1 day before
        if data[4] == 0 and (-epsilon < divmod(((now - event1d).total_seconds()), 60)[0] < epsilon):
            # update db
            cursor.execute(
                f"UPDATE `csg_automations`.`eventNotification` SET `oneDay` = 1 WHERE `eventId` = {eventid}")
            conn.commit()
            # send alert
            webhook = DiscordWebhook(url=uri,
                                     content=f"@everyone Hey reminder bot here,\n CSG will be hosting {event['summary']}"
                                             f" tomorrow, the {eventTime.day} at {eventTime.time}. "
                                             f"We hope to see everyone their!\n"
                                             f"------------------------------"
                                             f"Details: {event['description']}")
            response = webhook.execute()
            print(response)

        # send an alert for 3 days before
        if data[5] == 0 and (-epsilon < divmod(((now - event30min).total_seconds()), 60)[0] < epsilon):
            # update db
            cursor.execute(
                f"UPDATE `csg_automations`.`eventNotification` SET `thirtyMinutes` = 1 WHERE `eventId` = {eventid}")
            conn.commit()
            # send alert
            webhook = DiscordWebhook(url=uri, content=f"@everyone Hey reminder bot here,\n CSG will be hosting "
                                                      f"{event['summary']} in 30 minutes!"
                                                      f"Don't forget to join in!\n"
                                                      f"------------------------------"
                                                      f"Details: {event['description']}")
            response = webhook.execute()
            print(response)
