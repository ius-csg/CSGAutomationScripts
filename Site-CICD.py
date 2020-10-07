from zipfile import ZipFile
import wget
import os
import paramiko
from scp import SCPClient
import sys


def progress(filename, size, sent):
    sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100))


ssh = paramiko.SSHClient()

ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Downloading file")

file = "./CSGSite.zip"

url = "https://github.com/ius-csg/csghomepage/releases/download/latest/release.zip"

wget.download(url, file, wget.bar_thermometer)

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