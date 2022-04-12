from requests import get
from io import BytesIO
from PIL import Image
from datetime import datetime
from google.oauth2.service_account import Credentials
import json
from util import Globals


def getFormattedDatetime(asPath=False):
    time = datetime.now()
    if asPath:
        return time.strftime("%d-%m-%Y_%H-%M-%S")
    return time.strftime("%d/%m/%Y %H:%M:%S")


def initializeLog():
    name = getFormattedDatetime(asPath=True) + ".txt"
    path = Globals.LOG_PATH + name
    open(path, "w").close()
    Globals.setLogFile(name)
    return path


def log(text, depth=0):
    msg = "[" + getFormattedDatetime() + "] " + ("--> " * depth) + text
    if Globals.LOG:
        with open(Globals.LOG_PATH + Globals.LOG_FILE, "a") as f:
            f.write(msg + "\n")
    if Globals.DEBUG:
        print(msg)


def readJSON(path):
    data = ""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def writeJson(path, data):
    text = json.dumps(data)
    with open(path, 'w+') as outfile:
        outfile.write(text)


def fetchImage(url, size=None):
    response = get(url)
    image = Image.open(BytesIO(response.content))
    if size:
        image.resize(size)
    return image


def fromWei(wei, precision=2):
    return round((int(wei) / 1000000000000000000), precision)


def readServiceAccountCredentials(path):
    return Credentials.from_service_account_file(
        path, 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )