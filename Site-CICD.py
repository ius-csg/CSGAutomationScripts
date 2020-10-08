from zipfile import ZipFile
import wget
import os
import paramiko
from scp import SCPClient
import sys
import hashlib
import pyodbc
import datetime

def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100))


password = sys.argv[1]

# Download the build file
print("Downloading file")

url = "https://github.com/ius-csg/csghomepage/releases/download/latest/release.zip"

file = "./CSGSite.zip"

wget.download(url, file, wget.bar_thermometer)

# Talk to db and compare the build numbers

# if same stop

# if different continue and update


# Talk to db and compare the hashes
# conn = pyodbc.connect('Driver=MySQL ODBC 8.0 ANSI Driver;'
#                       'Server=192.168.1.101;'
#                       'Database=csg_automation;'
#                       'Trusted_Connection=yes;'
#                       'UID=app0005;'
#                       'PWD={};'.format(password))
#
# cursor = conn.cursor()
#
# currentHash = cursor.execute( "SELECT hash,  FROM csg_automations.CI/CD where project = \"CI/CD\" and datetimeInserted=(SELECT MAX(datetimeInserted) FROM csg_automations.CI/CD WHERE project = \"CI/CD\" )")
#
# # Stop execution since their is no change in the release
# if currentHash == thisHash:
#     exit(0)
#
# cursor.execute("INSERT INTO csg_automations.CI/CD (project , hash, datetimeInserted ) VALUES ( \"CI/CD\", \"{}\",\"{}\");".format(thisHash, datetime.datetime.now()))



# Set up ssh connection

ssh = paramiko.SSHClient()

ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

with ZipFile(file, 'r') as zipObj:
    zipObj.extractall("./release")

ssh.connect("192.168.3.4", 22, "root", "local#123")

scp = SCPClient(ssh.get_transport(), progress=progress)

stdin, stdout, stderr = ssh.exec_command('cd /var/www/csghomepage/')

print(stdout)

scp.put('./release/_site', 'temp', True)

stdin, stdout, stderr = ssh.exec_command('mv _site _site.old')

print(stdout)

stdin, stdout, stderr = ssh.exec_command('mv temp _site')

print(stdout)

stdin, stdout, stderr = ssh.exec_command('rm -rf _site.old')

print(stdout)

print("Cleaning up local directory")

os.remove("CSGSite.zip")

os.rmdir("./release")