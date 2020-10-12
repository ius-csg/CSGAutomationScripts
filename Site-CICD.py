import shutil
from zipfile import ZipFile
import requests
import os
import paramiko
from scp import SCPClient
import sys
import mysql.connector
from discord_webhook import DiscordWebhook


def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100))


# ----- Start script -----
password = sys.argv[1]

buildchannelid = sys.argv[2]

buri = "https://discordapp.com/api/webhooks/{}".format(buildchannelid)

alertchannelid = sys.argv[3]

auri = "https://discordapp.com/api/webhooks/{}".format(alertchannelid)

# Download the build file
print("Downloading file")

url = "https://github.com/ius-csg/csghomepage/releases/download/latest/release.zip"

file = "./CSGSite.zip"

open(file, 'wb').write(requests.get(url, allow_redirects=True).content)

#wget.download(url, file)

print("Unzipping file")

with ZipFile(file, 'r') as zipObj:
    zipObj.extractall("./release")

# Get build number
with open("release/_site/BUILD_NUMBER") as f:
    bfile = f.read()

buildNum = [int(i) for i in bfile.split() if i.isdigit()][0]

try:
    conn = mysql.connector.connect(
        user="app0005",
        password=password,
        host="192.168.1.101",
        port=3306,
        database="csg_automations"
    )

except mysql.connector.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

print("Connecting to database ")

cursor = conn.cursor()

# Talk to db and compare the build numbers
cursor.execute("SELECT * FROM csg_automations.CICD WHERE project='csgwebsite'")

cbuild = cursor.fetchone()

# if same stop otherwise continue and update
if cbuild is None:
    # if empty insert new build
    cursor.execute(f"INSERT INTO `csg_automations`.`CICD` (`project`,`buildNum`,`status`) VALUES ('csgwebsite', {buildNum}, 'pending');")
    conn.commit()
    print("CSGWebsite build was updated")
else:
    cbuildNum = cbuild[2]
    status = cbuild[3]
    if cbuildNum is buildNum and status == 'success':
        print("Build Version the same")
        sys.exit(0)

# try to connect to the server and update the site
try:
    # Set up ssh connection
    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(hostname="192.168.3.4", port=22, username='root', password="local#123")

    with SCPClient(ssh.get_transport()) as scp:
        scp.put('./release/_site', '/var/www/csghomepage/temp', recursive=True)  # Copy my_file.txt to the server

    stdin, stdout, stderr = ssh.exec_command('cd /var/www/csghomepage/; mv _site _site.old; mv temp _site; rm -rf _site.old;')

    print(stdout)

    cursor.execute("UPDATE `csg_automations`.`CICD` SET `status` = 'success' WHERE `project` = 'csgwebsite';")
    conn.commit()
    print("CSGWebsite build was updated successfully")

    webhook = DiscordWebhook(url=buri, content='CSG Website was successfully deployed. :white_check_mark: ')
    response = webhook.execute()

except:
    cursor.execute("UPDATE `csg_automations`.`CICD` SET `status` = 'failed' WHERE `project` = 'csgwebsite';")
    conn.commit()
    print("CSGWEBSITE deployment failed")
    webhook = DiscordWebhook(url=auri, content=' :warning: CSG Website deployment failed. !!! :warning:')
    response = webhook.execute()

finally:
    print("Cleaning up local directory")

    os.remove("CSGSite.zip")

    shutil.rmtree("./release")
