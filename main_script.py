# IMPORTING PACKAGES
import os
import numpy as np
import pandas as pd
import datetime as dt
from twilio.rest import Client # to send SMS
import schedule # to schedule the task at a certain time
import time # to set the task to a certain time
from datetime import date
import yfinance as yf
import yfinance.shared as shared
from webserver import keep_alive

# ticker watchlist
ticker_name = {'AAPL':'Apple','MSFT':'Microsoft','GOOG':'Alphabet (Google)','AMZN':'Amazon','FB':'Facebook','TSLA':'Tesla','V':'Visa','NVDA':'Nvidia','JPM':'JP Morgan','JNJ':'Johnson & Johnson','WMT':'Walmart','UNH':'UnitedHealth','MA':'Mastercard','HD':'Home Depot','PG':'Procter & Gamble','PYPL':'PayPal','BAC':'Bank of America','DIS':'Walt Disney','ADBE':'Adobe','NKE':'Nike','CMCSA':'Comcast','LLY':'Eli Lilly','PFE':'Pfizer','ORCL':'Oracle','KO':'Coca-Cola','CRM':'Salesforce','XOM':'Exxon Mobil','CSCO':'Cisco','NFLX':'Netflix','DHR':'Danaher','INTC':'Intel','ABT':'Abbott Laboratories','PEP':'Pepsico','TMO':'Thermo Fisher Scientific','ABBV':'AbbVie','AVGO':'Broadcom','COST':'Costco','CVX':'Chevron','WFC':'Wells Fargo','MS':'Morgan Stanley','TXN':'Texas Instruments','MCD':'McDonalds','MRNA':'Moderna','UPS':'United Parcel Service','QCOM':'QUALCOMM','HON':'Honeywell','NEE':'Nextera Energy','PM':'Philip Morris','BMY':'Bristol-Myers','INTU':'Intuit','UNP':'Union Pacific Corporation','CHTR': 'Charter Communications','C':'Citigroup','SBUX':'Starbucks','AMD':'AMD','BLK':'BlackRock','LOW':"Lowe's Companies",'BA':'Boeing','AXP':'American Express','AMGN':'Amgen','RTX':'Raytheon Technologies','SCHW':'Charles Schwab','AMAT':'Applied Materials','SQ':'Square','GS':'Goldman Sachs','TGT':'Target','AMT':'American Tower','IBM':'IBM','SNAP':'Snapchat','ISRG':'Intuitive Surgical','EL':'Estee Lauder','ZM':'Zoom','NOW':'ServiceNow','MMM':'3M','DE':'Deere & Company','CAT':'Caterpillar','GE':'General Electric','SPGI':'S&P Global','CVS':'CVS Health','LMT':'Lockheed Martin','SYK':'Stryker Corporation','ZTS':'Zoetis','PLD':'Prologis','ABNB':'Airbnb','LRCX':'Lam Research','ANTM':'Anthem','MU':'Micron Technology','BKNG':'Booking.com','ADP':'Automatic Data Processing','MO':'Mondelez','CCI':'Crown Castle','BX':'Blackstone Group','DUK':'Duke Energy'}

tickers = list(ticker_name.keys()) # tickers

moving_averages = ['SMA50','SMA100','SMA200']
stocks_bought = {} # list storing all stocks that have had a buy signal but no sell signal yet
stocks_traded = [] # list storing all stocks ever traded, including: buy price and date, and the same for sell

# Keep this repl running forever using uptime robot
keep_alive()

def get_data():
    
    # Downloading the data for all tickers
    print('data gathered')
    downloaded_data = yf.download(tickers,interval='1d',period='5y') # download the data
    
    # Remove tickers with no data at all
    failed_tickers = shared._ERRORS.keys() # see which tickers have no data whatsoever
    for failed_ticker in failed_tickers:
        downloaded_data.drop([('Adj Close',failed_ticker),('Close',failed_ticker),('High',failed_ticker),('Low',failed_ticker),('Open',failed_ticker),('Volume',failed_ticker)], axis=1) # remove the failed tickers from the dataframe

    # Remove tickers that have more than 8% nan values in the last 200 days and which we do not have a current position in right now
    for ticker_not_bought in list(set(tickers) - set(list(stocks_bought.keys()))):
      if (downloaded_data.iloc[-200:].loc[:,('Adj Close',ticker_not_bought)].isna().sum() / 200) > 0.08:
        downloaded_data.drop([('Adj Close',ticker_not_bought),('Close',ticker_not_bought),('High',ticker_not_bought),('Low',ticker_not_bought),('Open',ticker_not_bought),('Volume',ticker_not_bought)], axis=1) # remove the failed tickers from the dataframe

    # Removing nan values by first forward fill and then backfill if a nan value on the first date (ie. date furthest from now) 
    downloaded_data.fillna(method='ffill', axis=0, inplace=True)
    downloaded_data.fillna(method='bfill', axis=0, inplace=True)

    # Creating an empty dataframe of correct dimensions to store the data
    processed_data = pd.DataFrame(index=downloaded_data.index, columns=pd.MultiIndex.from_product([tickers,['Adj Close']+moving_averages]))
    
    for stock in tickers:
        
      # Inserting close data
      processed_data.loc[:,(stock,'Adj Close')] = downloaded_data.loc[:,('Adj Close',stock)]
      
      # Calculating and inserting SMA data
      for sma in moving_averages:
        # sma[3:] is the period (eg. 50, 100, or 200)
        processed_data.loc[:,(stock,sma)] = downloaded_data.loc[:,('Adj Close',stock)].rolling(int(sma[3:])).mean()
    
    # Drop the unecessary rows. Only need to keep the last four rows.
    processed_data = processed_data.iloc[-4:]

    # Flip the dataframe so that the most recent data is at the top
    processed_data = processed_data.iloc[::-1]

    # Reset the index and drop the old one
    processed_data = processed_data.reset_index()
    processed_data = processed_data.drop(('Date',''), axis=1)

    # Check if today is the last row in processed data. If yes then check for signals
    check_signals(processed_data)


def check_signals(processed_input: pd.DataFrame()):
  print('called check signals')
  # CHECK ALL STOCKS FOR BUY SIGNALS
  for stock in tickers:

    close = processed_input.loc[:,(stock,'Adj Close')]  
    sma200 = processed_input.loc[:,(stock,'SMA200')]
    sma100 = processed_input.loc[:,(stock,'SMA100')]
    sma50 = processed_input.loc[:,(stock,'SMA50')]

    lowest_ma = sma50 # Declare the lowest moving average variable and randomly assign to SMA 50. This is needed for the buy signal
    highest_ma = sma50 # Declare the highest moving average variable and randomly assign to SMA 50. This is needed for the sell signal
    lowest_ma_string = ''
    highest_ma_string = ''
      
    # Finding the lowest simple moving average (SMA)
    if sma50[2] < sma100[2]:
        # SMA50 is less than SMA100
        if sma50[2] < sma200[2]:
            # SMA50 is less than SMA100 and SMA200
            lowest_ma = sma50
            lowest_ma_string = 'SMA50'
            highest_ma = sma200
            highest_ma_string = 'SMA200'
        else:
            # SMA50 is less than SMA100 but not less than SMA200. So SMA200 is the lowest
            lowest_ma = sma200
            lowest_ma_string = 'SMA200'
            highest_ma = sma50
            highest_ma_string = 'SMA50' 
    else:
        # SMA100 is less than SMA50
        if sma100[2] < sma200[2]:
            # SMA100 is less than SMA50 and SMA200
            lowest_ma = sma100
            lowest_ma_string = 'SMA100'
        else:
            # SMA100 is less than SMA50 but not less than SMA200. So SMA200 is the lowest
            lowest_ma = sma200
            lowest_ma_string = 'SMA200'
    
    # Finding the crossover between the price and the lowest moving average
    ## Check if the close is above the lowest MA today
    if close[0] > lowest_ma[0]:
      ## Check if the close is above the lowest MA yesterday
      if close[1] > lowest_ma[1]:
        ## Check if the close is above the lowest MA the day before
        if close[2] > lowest_ma[2]:
          ## Check if the close was below the MA three days ago to see if there was a crossover two days ago (total 3 days above then including today)
          if close[3] < lowest_ma[3]:
            ### It has been three days since the stock crossed over. Time to buy!
            stocks_bought[stock] = [date.today(), close[0]]
            stocks_traded.append([stock, 'buy', date.today(), close[0]])
            
            send_sms(text=f'{ticker_name[stock]} ({stock}) crossed above the {lowest_ma_string} four days ago and has been above since. {stock} closed at a price of ${close[0]} today. Remember to buy tomorrow!', recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code
            continue # end this iteration of the loop without checking for a rebound off the lowest SMA
        
        else:
          ### Crossed above yesterday. It has been above the MA for two days
          send_sms(text=f'{ticker_name[stock]} ({stock}) has stayed above the {lowest_ma_string} for two days in a row. {stock} closed at a price of ${close[0]} today. I will let you know if it closes above the {lowest_ma_string} tomorrow.', recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code
          continue # end this iteration of the loop without checking for a rebound off the lowest SMA
      else:
        ### The stock closed above the lowest MA today but not yesterday (ie. crossover today!)
        send_sms(text=f'{ticker_name[stock]} ({stock}) crossed above the {lowest_ma_string} today! {stock} closed at a price of ${close[0]}.', recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code
        continue # end this iteration of the loop without checking for a rebound off the lowest SMA

  # CHECK STOCKS ALREADY BOUGHT FOR SELL SIGNALS
  for stock in list(stocks_bought):
    # Sell if the closing price went below the SMA50 or SMA200 three days ago
    ## Check if the close is below one of the MAs today
    if close[0] < highest_ma[0]:
      ## Check if the close is below one of the MAs yesterday
      if close[1] < highest_ma[1]:
        ## Check if the close is below the lowest MA the day before
        if close[2] < highest_ma[2]:
          ## Check if the close was above the MA three days ago to see if there was a crossover two days ago (total 3 days below then including today)
          if close[3] > highest_ma[3]:
            ### It has been three days since the stock crossed below. Time to sell!
            delta = date.today() - stocks_bought[stock][0] # find the number of days the trade was held
            profit = round((close[0]/stocks_bought[stock][1])-1,2)*100 # calculate the profit or loss

            stocks_bought.pop(stock)
            stocks_traded.append([stock, 'sell', date.today(), close[0]])
            
            if profit > 0:
              # Made a profit. Happy message
              send_sms(text=f"{ticker_name[stock]} ({stock}) crossed below the {lowest_ma_string} four days ago and has been below since. {stock} closed at a price of ${close[0]} today. That's a {profit}% profit in "+str(delta.days)+" days! Congrats! Remember to sell tomorrow!", recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code
            else:
              # Made a loss. Sad message
              send_sms(text=f"{ticker_name[stock]} ({stock}) crossed below the {lowest_ma_string} four days ago and has been below since. {stock} closed at a price of ${close[0]} today. Unfortunately, that's a {profit}% loss. Remember to sell tomorrow.", recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code
        
        else:
          ### Crossed below yesterday. It has been below the MA for two days
          send_sms(text=f'{ticker_name[stock]} ({stock}) has stayed below the {lowest_ma_string} for two days in a row. {stock} closed at a price of ${close[0]} today. I will let you know if it closes below the {lowest_ma_string} tomorrow.', recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code
          
      else:
        ### The stock closed above the lowest MA today but not yesterday (ie. crossover today!)
        send_sms(text=f'{ticker_name[stock]} ({stock}) crossed below the {lowest_ma_string} today! {stock} closed at a price of ${close[0]}.', recipients=['+44XXXXXXXXXX','+65XXXXXXXXXX']) # remember to include the country code

# SEND SMS
def send_sms(text: str, recipients: list):
  for recipient in recipients:
    account_sid = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' # remember to insert your own tokens in this line and the line below
    auth_token = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' # https://www.twilio.com/docs/iam/access-tokens
    client = Client(account_sid, auth_token)

    message = client.messages \
                    .create(
                        body=text,
                        from_='+XXXXXX',
                        to=recipient
                    )
    # CHANGE WHICH NUMBER IT IS BEING SENT FROM. Check your Twilio account for this.
    print(message.sid) # prints a code if the message has been successfully sent 


# SCHEDULE WHEN TO RUN EVERYTHING
## The schedule does not clear even if you cancel a run and start it again so need to clear the schedule every time it is run and then re-declare the schedule
schedule.clear()

schedule.every().tuesday.at("03:00").do(get_data) # Run at 3am UTC time (ie. 11pm NY time and 7am Dubai Time)
schedule.every().wednesday.at("03:00").do(get_data) # Run at 3am UTC time (ie. 11pm NY time and 7am Dubai Time)
schedule.every().thursday.at("03:00").do(get_data) # Run at 3am UTC time (ie. 11pm NY time and 7am Dubai Time)
schedule.every().friday.at("03:00").do(get_data) # Run at 3am UTC time (ie. 11pm NY time and 7am Dubai Time)
schedule.every().saturday.at("03:00").do(get_data) # Run at 3am UTC time (ie. 11pm NY time and 7am Dubai Time)

# Keep the schedule running perpetually. The while loop checks if there is task the scheduler must run.
while True:
    schedule.run_pending()
    time.sleep(1)