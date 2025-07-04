

from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
import os
from finbert_utilis import estimate_sentiment
API_KEY = os.getenv("ALPACA_API_KEY", "PKLIKMZ0JPC2QUCDJYUW")
API_SECRET = os.getenv("ALPACA_API_SECRET", "de7WtuQvnl3uD3vDssAQnmTWCcTFiFQt17IWjaeQ")
BASE_URL = "https://paper-api.alpaca.markets/v2"
ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class MLTrader(Strategy):
    def initialize(self, symbol: str = "SPY",cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.api = REST(base_url=BASE_URL, key_id = API_KEY , secret_key=API_SECRET)
 
    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash*self.cash_at_risk / last_price,0)
        return cash,last_price,quantity
    
    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days = 3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self):
        today , three_days_prior = self.get_dates()
        news = self.api.get_news(symbol = self.symbol,start = three_days_prior,end = today)

        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        proability,sentiment = estimate_sentiment(news)
        return  proability,sentiment

    def on_trading_iteration(self):
        cash,last_price,quantity = self.position_sizing()
        probability,sentiment = self.get_sentiment()
        self.log(f"Starting iteration - Cash: {self.get_cash()}")
        if cash > last_price:
            if sentiment == "positive" and probability > .999:
                if self.last_order == "sell":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price*1.20 #20% up
                    stop_loss_price = last_price*0.95

                )
            self.submit_order(order)
            self.last_trade = "buy"
            self.log(f"Submitted Buy Order for {self.symbol}")
        elif sentiment == "negative" and probability > .999:
                if self.last_order == "buy":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",
                    take_profit_price=last_price*0.8 #20% up
                    stop_loss_price = last_price*1.05

                )
            self.submit_order(order)
            self.last_trade = "buy"
            self.log(f"Submitted Buy Order for {self.symbol}")


        self.log(f"Current Positions: {self.get_positions()}")

start_date = datetime(2023, 12, 15)

end_date = datetime(2023, 12, 31)
broker = Alpaca(ALPACA_CREDS)

strategy = MLTrader(name='ml_trader', broker=broker, parameters={"symbol": "SPY","cash_at_risk":.5})

strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol": "SPY"}
)
