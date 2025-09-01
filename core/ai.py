# Import all necessary libraries for data retrieval, analysis, and trading.
import pandas as pd
import numpy as np
import os
import joblib
import alpaca_trade_api as tradeapi
import yfinance as yf
from ta.volatility import average_true_range, BollingerBands
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from datetime import datetime, timedelta
import time
import pytz
import warnings
import sys
import matplotlib.pyplot as plt
import csv

# Suppress all warnings for a cleaner output
warnings.filterwarnings('ignore')

# --- Helper Functions ---
# A helper function to log all actions with a timestamp.
def log_action(message):
    """Logs a message to the console and a text file with a timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    try:
        with open('trading_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"{full_message}\n")
    except IOError as e:
        print(f"Error writing to log file: {e}")
    print(full_message)

def log_daily_summary(daily_stats, current_equity):
    """Logs the end-of-day performance summary to a CSV and the console."""
    try:
        file_exists = os.path.isfile('daily_performance.csv')
        with open('daily_performance.csv', 'a', newline='') as f:
            writer = csv.writer(f) 
            if not file_exists:
                writer.writerow(['Date', 'Total Trades', 'Total P/L', 'Win Rate (%)', 'Daily High Equity', 'Daily End Equity'])
            
            total_pl = daily_stats['total_profit'] + daily_stats['total_loss']
            win_rate = (daily_stats['wins'] / daily_stats['trades'] * 100) if daily_stats['trades'] > 0 else 0

            writer.writerow([
                datetime.now().strftime('%Y-%m-%d'),
                daily_stats['trades'],
                f"{total_pl:.2f}",
                f"{win_rate:.2f}",
                f"{daily_stats['daily_high_equity']:.2f}",
                f"{current_equity:.2f}"
            ])

        log_action("--- Daily Performance Summary ---")
        log_action(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        log_action(f"Total Trades: {daily_stats['trades']}")
        log_action(f"Total P/L: ${total_pl:.2f}")
        log_action(f"Win Rate: {win_rate:.2f}%")
        log_action(f"Daily High Equity: ${daily_stats['daily_high_equity']:.2f}")
        log_action(f"Daily End Equity: ${current_equity:.2f}")
        log_action("-------------------------------")
    except Exception as e:
        log_action(f"Error logging daily summary: {e}")

def generate_performance_dashboard():
    """Generates and saves a performance dashboard chart from the CSV data."""
    try:
        if not os.path.isfile('daily_performance.csv'):
            log_action("No performance data found to generate dashboard.")
            return

        df = pd.read_csv('daily_performance.csv')
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

        if df.empty:
            log_action("Performance data is empty. Cannot generate dashboard.")
            return

        plt.style.use('dark_background')
        fig, ax1 = plt.subplots(figsize=(12, 7), dpi=100)

        color = 'tab:blue'
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Daily End Equity ($)', color=color)
        ax1.plot(df.index, df['Daily End Equity'], color=color, marker='o', linestyle='-', linewidth=2, label='Daily End Equity')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.7)
        ax1.set_title('Trading Bot Performance Dashboard', fontsize=18, pad=20)
        plt.xticks(rotation=45)
        plt.tight_layout()
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        color = 'tab:orange'
        ax2.set_ylabel('Total P/L ($)', color=color)
        ax2.bar(df.index, df['Total P/L'].astype(float), color=color, alpha=0.5, width=0.8, label='Daily P/L')
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.legend(loc='upper right')

        fig.savefig('performance_dashboard.png')
        log_action("Performance dashboard generated and saved as performance_dashboard.png")

    except Exception as e:
        log_action(f"Error generating performance dashboard: {e}")

def get_latest_features_with_retry(ticker, max_retries=5, delay_seconds=10):
    """Fetches stock data and calculates features with a retry mechanism."""
    for attempt in range(max_retries):
        try:
            # Increased period to ensure enough data points are available
            df = yf.download(tickers=ticker, period='7d', interval='1m')
            
            # Reset index and clean column names
            df.reset_index(inplace=True)
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df.rename(columns={df.columns[0]: 'datetime'}, inplace=True)
            df.set_index('datetime', inplace=True)

            # Remove rows with NaN or infinite values
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df.dropna(inplace=True)

            # Check if received data is empty or insufficient
            if df.empty or len(df) < 50:
                log_action("Received empty or insufficient data. Retrying...")
                time.sleep(delay_seconds)
                continue
            
            # Additional check to ensure we are not using a row with zero volume
            # and identical open/high/low/close prices
            if df.iloc[-1]['volume'] == 0 or (df.iloc[-1]['open'] == df.iloc[-1]['high'] == df.iloc[-1]['low'] == df.iloc[-1]['close']):
                log_action("Latest data point has zero volume or no price movement. Skipping this cycle.")
                time.sleep(delay_seconds)
                continue

            # Recalculate features on the cleaned data
            df['volume_change_pct'] = df['volume'].pct_change() * 100
            
            macd = MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
            df['macd_line'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
            df['bb_hband'] = bollinger.bollinger_hband()
            df['bb_lband'] = bollinger.bollinger_lband()
            df['bb_wband'] = bollinger.bollinger_wband()
            df['sma_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
            df['rsi_14'] = RSIIndicator(close=df['close'], window=14).rsi()
            df['atr_14'] = average_true_range(high=df['high'], low=df['low'], close=df['close'], window=14)
            df['daily_range_pct'] = (df['high'] - df['low']) / df['close'] * 100
            df['volatility_5_std'] = df['close'].rolling(window=5).std()
            df['volatility_20_std'] = df['close'].rolling(window=20).std()
            df['year'] = df.index.year
            df['month'] = df.index.month
            df['dayofweek'] = df.index.dayofweek
            for lag in [1, 5, 20]:
                df[f'lag_{lag}_close_return'] = df['close'].pct_change(lag) * 100
            df['gap_open_close_prev_pct'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100
            df['high_low_spread'] = df['high'] - df['low']
            df['open_close_spread'] = df['close'] - df['open']
            df['momentum_10d'] = df['close'].diff(10)
            
            df.dropna(inplace=True)
            if df.empty:
                return None, None

            return df.iloc[-1], df
        except Exception as e:
            log_action(f"Error fetching data on attempt {attempt + 1}: {e}")
            time.sleep(delay_seconds)
    log_action("Failed to get data after all retries.")
    return None, None

def is_market_open():
    """Checks if the stock market is currently open."""
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    if now.weekday() >= 5:
        return False, None
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, second=0, microsecond=0)
    return market_open <= now < market_close, market_open

def get_daily_trades_from_alpaca(api, symbol):
    """Fetches daily trade history from Alpaca API to update stats."""
    try:
        daily_stats_temp = {'trades': 0, 'wins': 0, 'losses': 0, 'total_profit': 0.0, 'total_loss': 0.0}
        orders = api.list_orders(
            status='closed',
            direction='desc',
            limit=50,
            symbols=[symbol]
        )
        trade_pairs = []
        buy_orders = [o for o in orders if o.side == 'buy' and o.filled_at]
        sell_orders = [o for o in orders if o.side == 'sell' and o.filled_at]
        
        for sell_order in sell_orders:
            matching_buy = next((buy for buy in buy_orders if buy.filled_at < sell_order.filled_at), None)
            if matching_buy:
                trade_pairs.append((matching_buy, sell_order))
                buy_orders.remove(matching_buy)

        log_action(f"Found {len(trade_pairs)} completed trade pairs for today.")
        daily_stats_temp['trades'] = len(trade_pairs)
        
        for buy, sell in trade_pairs:
            buy_price = float(buy.filled_avg_price)
            sell_price = float(sell.filled_avg_price)
            pl = (sell_price - buy_price) * float(sell.filled_qty)
            if pl > 0:
                daily_stats_temp['wins'] += 1
                daily_stats_temp['total_profit'] += pl
            else:
                daily_stats_temp['losses'] += 1
                daily_stats_temp['total_loss'] += pl
        return daily_stats_temp
    except Exception as e:
        log_action(f"Error fetching daily trades from Alpaca: {e}")
        return {'trades': 0, 'wins': 0, 'losses': 0, 'total_profit': 0.0, 'total_loss': 0.0}

# --- Configuration and API Keys ---
MODELS_DIR = 'core/model'
MODEL_FILENAME = 'final_model.pkl'
GLOBAL_STOCK_TICKER = 'NVDA'
API_KEY = "PKXQT5JM5432H9TMUCPE"
API_SECRET = "P7yoSEf4PCRR3YwO7rshYnBKbPkW6CYHfVXD3Ano"
BASE_URL = "https://paper-api.alpaca.markets"

RISK_PER_TRADE_PERCENT = 0.02
MAX_EQUITY_PER_TRADE = 0.25
SL_MULTIPLIER = 2.5
TP_MULTIPLIER = 5.0
MAX_API_RETRIES = 5
API_RETRY_DELAY = 10
MAX_TRADES_PER_DAY = 10 
MAX_DAILY_LOSS_PERCENT = 0.05

FORCED_TRADE_MODE = False
FORCED_TRADE_TIME_HOUR = 15

# Global variables for tracking trade state
last_trade_date = None
daily_stats = {'trades': 0, 'wins': 0, 'losses': 0, 'total_profit': 0.0, 'total_loss': 0.0, 'daily_high_equity': 0.0}
trailing_stop_price = None

MODEL_FEATURE_NAMES = [
    'macd_line', 'macd_signal', 'macd_diff', 'bb_hband', 'bb_lband', 'bb_wband',
    'sma_20', 'rsi_14', 'atr_14', 'daily_range_pct', 'volatility_5_std',
    'volatility_20_std', 'year', 'month', 'dayofweek',
    'lag_1_close_return', 'lag_5_close_return', 'lag_20_close_return',
    'gap_open_close_prev_pct',
    'volume', 'volume_change_pct', 'high_low_spread', 'open_close_spread', 'momentum_10d'
]

# --- Main Trading Loop ---
def main_trading_loop():
    """Contains the core logic for the trading bot."""
    global daily_stats
    global trailing_stop_price
    global last_trade_date

    try:
        log_action("Loading the model...")
        model_path = os.path.join(MODELS_DIR, MODEL_FILENAME)
        final_model = joblib.load(model_path)
        log_action("Model loaded successfully.")
    except FileNotFoundError:
        log_action(f"Error: Model file not found at: {model_path}")
        return

    try:
        log_action("Connecting to Alpaca API...")
        api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
        account = api.get_account()
        log_action("Successfully connected to Alpaca API.")
        log_action(f"Account status: {account.status}")
        log_action(f"Current portfolio value: ${float(account.equity):.2f}")
        daily_stats['daily_high_equity'] = float(account.equity)
    except Exception as e:
        log_action(f"Error connecting to Alpaca API: {e}")
        return

    log_action("--- Automated trading system started ---")
    if FORCED_TRADE_MODE:
        log_action(f"WARNING: Forced Trade Mode is ACTIVE. Forced trade will occur at {FORCED_TRADE_TIME_HOUR}:00 ET.")
    else:
        log_action("Forced Trade Mode is inactive.")
    log_action("The code will now check the market every 180 seconds during market hours.")

    last_trade_date = (datetime.now() - timedelta(days=1)).date()

    while True:
        try:
            now = datetime.now(pytz.timezone('America/New_York'))
            
            if now.date() != last_trade_date:
                try:
                    account_info_eod = api.get_account()
                    end_of_day_equity = float(account_info_eod.equity)
                except Exception:
                    end_of_day_equity = daily_stats['daily_high_equity']

                log_daily_summary(daily_stats, end_of_day_equity)
                generate_performance_dashboard()
                
                log_action("New day detected. Fetching trade history from Alpaca.")
                daily_stats_from_alpaca = get_daily_trades_from_alpaca(api, GLOBAL_STOCK_TICKER)
                
                daily_stats = {'trades': 0, 'wins': 0, 'losses': 0, 'total_profit': 0.0, 'total_loss': 0.0, 'daily_high_equity': 0.0}
                daily_stats.update(daily_stats_from_alpaca)
                
                last_trade_date = now.date()
                try:
                    account_info = api.get_account()
                    daily_stats['daily_high_equity'] = float(account_info.equity)
                except Exception as e:
                    log_action(f"Error getting daily high equity at start of day: {e}")
            
            market_is_open, market_open_time = is_market_open()

            log_action("Checking the market...")

            if not market_is_open:
                log_action("Market is currently closed. Will re-check at the next scheduled time.")
                time.sleep(60)
                continue
                
            account_info = api.get_account()
            current_equity = float(account_info.equity)
            if current_equity > daily_stats['daily_high_equity']:
                daily_stats['daily_high_equity'] = current_equity
            
            if (daily_stats['daily_high_equity'] - current_equity) / daily_stats['daily_high_equity'] >= MAX_DAILY_LOSS_PERCENT:
                log_action(f"DAILY LOSS LIMIT REACHED! Total loss exceeds {MAX_DAILY_LOSS_PERCENT*100}%. Stopping all trades for today.")
                time.sleep(180)
                continue

            if daily_stats['trades'] >= MAX_TRADES_PER_DAY:
                log_action(f"DAILY TRADE LIMIT REACHED! {MAX_TRADES_PER_DAY} trades executed. No more trades today unless forced.")
                if FORCED_TRADE_MODE and now.time() < now.replace(hour=FORCED_TRADE_TIME_HOUR, minute=0, second=0).time():
                    time.sleep(180)
                    continue
                else:
                    time.sleep(180)
                    continue

            latest_data, full_df = get_latest_features_with_retry(GLOBAL_STOCK_TICKER)
            if latest_data is None or latest_data.isnull().values.any():
                log_action("Data quality check failed. Skipping this cycle.")
                time.sleep(180)
                continue
            
            log_action(f"--- Latest Feature Data ---\n{latest_data.to_string()}\n---------------------------")

            current_price = latest_data['close']
            log_action(f"Current price: ${current_price:.2f}")

            features_for_prediction_df = pd.DataFrame([latest_data])
            features_for_prediction_df = features_for_prediction_df[MODEL_FEATURE_NAMES]
            prediction = final_model.predict(features_for_prediction_df)[0]

            positions = api.list_positions()

            if not positions:
                is_normal_buy_signal = (prediction == 1)
                is_smart_buy_signal = is_normal_buy_signal and (latest_data['close'] > full_df['close'].iloc[-2]) and (latest_data['macd_line'] > latest_data['macd_signal'])
                is_forced_buy_signal = FORCED_TRADE_MODE and now.time() >= now.replace(hour=FORCED_TRADE_TIME_HOUR, minute=0, second=0).time()

                if is_smart_buy_signal or is_forced_buy_signal:
                    if not is_smart_buy_signal and not is_forced_buy_signal:
                        log_action(f"Model predicts BUY, but conditions are not strong enough. HOLDING.")
                        time.sleep(180)
                        continue
                    
                    log_action(f"Prediction is BUY and signal is strong. Calculating position size based on risk...")
                    
                    account_info = api.get_account()
                    total_equity = float(account_info.equity)
                    
                    risk_amount = total_equity * RISK_PER_TRADE_PERCENT
                    stop_loss_distance = latest_data['atr_14'] * SL_MULTIPLIER
                    shares_to_buy = int(risk_amount / stop_loss_distance) if stop_loss_distance > 0 else 0
                    
                    max_dollar_amount_per_trade = total_equity * MAX_EQUITY_PER_TRADE
                    max_shares_affordable_by_cap = int(max_dollar_amount_per_trade / current_price)
                    max_shares_affordable = int(total_equity / current_price)
                    shares_to_buy = min(shares_to_buy, max_shares_affordable_by_cap, max_shares_affordable)

                    if shares_to_buy > 0:
                        log_action(f"Calculated position size: {shares_to_buy} shares.")
                        try:
                            api.submit_order(
                                symbol=GLOBAL_STOCK_TICKER,
                                qty=shares_to_buy,
                                side='buy',
                                type='market',
                                time_in_force='day'
                            )
                            daily_stats['trades'] += 1
                            log_action(f"BUY signal! Executing order for {shares_to_buy} shares at ${current_price:.2f}.")
                            last_trade_date = now.date()
                            trailing_stop_price = current_price - (latest_data['atr_14'] * SL_MULTIPLIER)
                        except Exception as e:
                            log_action(f"API Error during buy order: {e}")
                    else:
                        log_action("Calculated shares to buy is zero. Capital or risk is too low.")
                else:
                    log_action(f"Model does not recommend buying at the moment. Prediction: {prediction}. No action taken.")

            else:
                position = positions[0]
                entry_price = float(position.avg_entry_price)
                
                if trailing_stop_price is not None:
                    new_trailing_stop = current_price - (latest_data['atr_14'] * SL_MULTIPLIER)
                    if new_trailing_stop > trailing_stop_price:
                        trailing_stop_price = new_trailing_stop
                        log_action(f"Trailing Stop-Loss updated to ${trailing_stop_price:.2f}")

                take_profit_price = entry_price + (latest_data['atr_14'] * TP_MULTIPLIER)
                current_profit = (current_price - entry_price) / entry_price
                trailing_stop_display = f"${trailing_stop_price:.2f}" if trailing_stop_price is not None else "N/A"
                log_action(f"Trade status: Current P/L: {current_profit * 100:.2f}%. Trailing SL: {trailing_stop_display}, TP: ${take_profit_price:.2f}")

                is_sell_triggered = False
                pl = (current_price - entry_price) * float(position.qty)
                
                if (trailing_stop_price is not None and current_price <= trailing_stop_price) or (current_price >= take_profit_price) or (prediction == 0):
                    sell_reason = ""
                    if trailing_stop_price is not None and current_price <= trailing_stop_price:
                        sell_reason = "Trailing Stop-Loss"
                    elif current_price >= take_profit_price:
                        sell_reason = "Dynamic Take Profit"
                    elif prediction == 0:
                        sell_reason = "Model Prediction Change (from BUY to SELL)"

                    log_action(f"SELL signal! Closing trade ({sell_reason}) at ${current_price:.2f}. Return: {current_profit * 100:.2f}%")
                    
                    try:
                        api.close_position(GLOBAL_STOCK_TICKER)
                        log_action(f"Successfully closed position.")
                        trailing_stop_price = None
                        daily_stats['trades'] += 1
                        if pl > 0:
                            daily_stats['wins'] += 1
                            daily_stats['total_profit'] += pl
                        else:
                            daily_stats['losses'] += 1
                            daily_stats['total_loss'] += pl
                    except Exception as e:
                        log_action(f"API Error during sell order: {e}")
        except Exception as e:
            log_action(f"A critical error occurred in the trading loop: {e}")
        finally:
            time.sleep(180)

# --- Main Execution Entry Point ---
if __name__ == "__main__":
    try:
        main_trading_loop()
    except KeyboardInterrupt:
        log_action("Automated trading system stopped by user.")
        try:
            # Final logging before exit
            api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
            account_info_eod = api.get_account()
            end_of_day_equity = float(account_info_eod.equity)
        except Exception:
            end_of_day_equity = daily_stats.get('daily_high_equity', 0.0)
        
        if daily_stats['trades'] > 0:
            log_daily_summary(daily_stats, end_of_day_equity)
            generate_performance_dashboard()