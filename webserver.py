# Repl will automatically stop your script from running after a certain amount of time if it believes to be inactive. 
# This script prevents that and must be linked to Uptime Robot for this to work.
# To get it working, make an account on Uptime Robot and click on: create a new monitor. Choose the type as 'HTTP(s)' and for the URL paste the one from repl that is outputted when you run your main script.
# Any monitoring interval less than 45 mins will work well. 
# Important: you should not change the name of this file or you will need to change line 12 of the main_script.py file

from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')

def home():
    return "I'm alive"

def run():
  app.run(host='0.0.0.0',port=8080)

def keep_alive():  
    t = Thread(target=run)
    t.start()