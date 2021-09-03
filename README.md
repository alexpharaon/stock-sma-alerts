# stock-sma-alerts
This is script is meant to be run on repl.it or some other server where you can run a script perpetually. It sends the user an SMS whenever a stock generates a buy signal, or, if a stock you own receives a sell signal. I used Twilio for sending the SMS's. To set it up, you need to make your own Twilio account and follow their documentation on how to link your account to your phone number (assuming you have the free account).

This stock strategy is best used after a market crash as it buys you in during the recovery and allows you to ride the bullish uptrend that typically takes place after a market rebound. The strategy waits for confirmation of a rebound which reduces risk of the market dropping further.
