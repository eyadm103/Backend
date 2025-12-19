# Import all necessary libraries for data retrieval, analysis, and trading.
import pandas as pd
import numpy as np
import os
import joblib
import alpaca_trade_api as tradeapi
from ta.volatility import average_true_range, BollingerBands
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from datetime import datetime, timedelta
import time
import pytz
import warnings
import sys
import matplotlib.pyplot as plt
import csv
import yfinance as yf
import json
import traceback

from django.core.management.base import BaseCommand
from django.conf import settings

# Suppress all warnings for a cleaner output
warnings.filterwarnings('ignore')

# FIX: Set display options to avoid scientific notation
pd.options.display.float_format = '{:.4f}'.format
np.set_printoptions(suppress=True, precision=4)

# --- Global State Variables ---
daily_stats = {
    'trades': 0, 'wins': 0, 'losses': 0,
    'total_profit': 0.0, 'total_loss': 0.0,
    'daily_high_equity': 0.0
}
highest_profit_pct = 0.0
last_trade_date = None
last_action = "None" # Added: New global variable to track the last action

# --- Helper Functions ---
def log_action(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    try:
        with open(settings.TRADING_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{full_message}\n")
    except IOError as e:
        print(f"Error writing to log file: {e}")
    print(full_message)

def log_daily_summary(daily_stats, current_equity):
    try:
        file_exists = os.path.isfile(settings.DAILY_PERFORMANCE_FILE)
        with open(settings.DAILY_PERFORMANCE_FILE, 'a', newline='') as f:
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
    try:
        if not os.path.isfile(settings.DAILY_PERFORMANCE_FILE):
            log_action("No performance data found to generate dashboard.")
            return
        df = pd.read_csv(settings.DAILY_PERFORMANCE_FILE)
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

# Modified: Added last_action and current_price parameters
def update_status_json(account_info, positions, daily_stats, current_price, last_action):
    try:
        status_data = {
            "id": 1,
            "bot_status": "Running",
            "last_update": datetime.now().isoformat(),
            "equity": f"{float(account_info.equity):.4f}",
            "cash": f"{float(account_info.cash):.4f}",
            "buying_power": f"{float(account_info.buying_power):.4f}",
            "trades_today": daily_stats['trades'],
            "wins": daily_stats['wins'],
            "losses": daily_stats['losses'],
            "total_profit": f"{daily_stats['total_profit']:.4f}",
            "total_loss": f"{daily_stats['total_loss']:.4f}",
            
            "ticker": None, # Modified: Changed 'symbol' to 'ticker' for clarity
            "qty": "0.0000",
            "entry_price": "0.0000",
            "current_value": "0.0000",
            "unrealized_pl": "0.0000",
            "current_price": f"{current_price:.4f}" if current_price else "N/A", # Added: Current Price
            "last_action": last_action # Added: Last Action
        }
        
        if positions:
            position = positions[0]
            entry_price = float(position.avg_entry_price)
            unrealized_pl = (current_price - entry_price) * float(position.qty) if current_price else 0.0
            
            status_data.update({
                "ticker": position.symbol,
                "qty": f"{float(position.qty):.4f}",
                "entry_price": f"{entry_price:.4f}",
                "current_value": f"{float(position.market_value):.4f}",
                "unrealized_pl": f"{unrealized_pl:.4f}"
            })
            
        with open(settings.STATUS_JSON_FILE, 'w') as f:
            json.dump([status_data], f, indent=4)
        
        log_action("Trading status saved to bot_status.json successfully.")
    except Exception as e:
        log_action(f"Error saving trading status to JSON file: {e}")

def get_latest_price_from_alpaca(api, ticker):
    try:
        latest_trade = api.get_latest_trade(ticker)
        return latest_trade.price
    except Exception as e:
        log_action(f"Error fetching latest price from Alpaca API: {e}")
        return None

def get_daily_data_for_sma(ticker, period='250d', interval='1d'):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.columns = [col.lower() for col in df.columns]
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        log_action(f"Error fetching daily data from Yahoo Finance: {e}")
        return pd.DataFrame()

def get_latest_intraday_data(ticker, period='5d', interval='2m'):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.reset_index(inplace=True)
        df.rename(columns={'Datetime': 'datetime', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        df.set_index('datetime', inplace=True)
        df.columns = [col.lower() for col in df.columns]
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        log_action(f"Error fetching intraday data from Yahoo Finance: {e}")
        return pd.DataFrame()
        
def calculate_features(df_intraday):
    REQUIRED_PERIOD = 34
    if df_intraday.empty or len(df_intraday) < REQUIRED_PERIOD:
        return None
    
    df = df_intraday.copy()
    if 'volume' not in df.columns:
        return None
        
    df['volume_change_pct'] = df['volume'].pct_change() * 100
    macd = MACD(close=df['close'], window_fast=12, window_slow=26, window_sign=9)
    df['macd_line'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    df['rsi_14'] = RSIIndicator(close=df['close'], window=14).rsi()
    df['atr_14'] = average_true_range(high=df['high'], low=df['low'], close=df['close'], window=14)
    bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_hband'] = bollinger.bollinger_hband()
    df['bb_lband'] = bollinger.bollinger_lband()
    df['bb_wband'] = bollinger.bollinger_wband()
    df['sma_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
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
        return None
    if 'atr_14' not in df.columns:
        return None
    return df.iloc[-1]

def is_market_open():
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    if now.weekday() >= 5:
        return False, None
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, second=0, microsecond=0)
    return market_open <= now < market_close, market_open


# --- The Main Trading Loop ---
class Command(BaseCommand):
    help = 'Runs the algorithmic trading bot.'

    def handle(self, *args, **options):
        global daily_stats
        global last_trade_date
        global highest_profit_pct
        global last_action # Added: New global variable

        log_action("--- Algorithmic Trading System Initiated ---")
        
        try:
            log_action("Loading the machine learning model...")
            model_path = os.path.join(settings.MODELS_DIR, settings.MODEL_FILENAME)
            final_model = joblib.load(model_path)
            log_action("Model loaded successfully.")
        except FileNotFoundError:
            log_action(f"Error: Model file not found at: {model_path}")
            return

        try:
            log_action("Connecting to Alpaca API...")
            api = tradeapi.REST(settings.API_KEY, settings.API_SECRET, settings.BASE_URL, api_version='v2')
            account = api.get_account()
            log_action("Connection to Alpaca API successful.")
            log_action(f"Account Status: {account.status}")
            log_action(f"Current Portfolio Equity: ${float(account.equity):.2f}")
            daily_stats['daily_high_equity'] = float(account.equity)
        except Exception as e:
            log_action(f"Error connecting to Alpaca API: {e}")
            return

        last_trade_date = (datetime.now() - timedelta(days=1)).date()

        while True:
            try:
                now = datetime.now(pytz.timezone('America/New_York'))
                
                if now.date() != last_trade_date:
                    account_info_eod = api.get_account()
                    end_of_day_equity = float(account_info_eod.equity)
                    log_daily_summary(daily_stats, end_of_day_equity)
                    generate_performance_dashboard()
                    
                    log_action("New day detected. Resetting daily statistics.")
                    daily_stats = {
                        'trades': 0, 'wins': 0, 'losses': 0,
                        'total_profit': 0.0, 'total_loss': 0.0,
                        'daily_high_equity': float(account_info_eod.equity)
                    }
                    highest_profit_pct = 0.0
                    last_action = "None" # Added: Reset last_action
                    last_trade_date = now.date()
                
                market_is_open, market_open_time = is_market_open()
                if market_open_time:
                    market_close_time = market_open_time.replace(hour=16, minute=0, second=0, microsecond=0)
                    time_to_close = (market_close_time - now).total_seconds()
                    if time_to_close <= 600 and not api.list_positions() and time_to_close > 0:
                        log_action("Less than 10 minutes until market close and no open positions. Halting new trades for the day.")
                        account_info = api.get_account()
                        positions = api.list_positions()
                        current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                        # Modified: Passed last_action and current_price
                        update_status_json(account_info, positions, daily_stats, current_price, last_action)
                        time.sleep(30)
                        continue
                
                if not market_is_open:
                    log_action("Market is currently closed. Checking again in 2 minutes.")
                    account_info = api.get_account()
                    positions = api.list_positions()
                    current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                    # Modified: Passed last_action and current_price
                    update_status_json(account_info, positions, daily_stats, current_price, last_action)
                    time.sleep(30)
                    continue
                    
                account_info = api.get_account()
                current_equity = float(account_info.equity)
                if current_equity > daily_stats['daily_high_equity']:
                    daily_stats['daily_high_equity'] = current_equity
                
                if daily_stats['daily_high_equity'] > 0 and \
                   (daily_stats['daily_high_equity'] - current_equity) / daily_stats['daily_high_equity'] >= settings.MAX_DAILY_LOSS_PERCENT:
                    log_action(f"Daily loss limit reached! Halting trading.")
                    positions = api.list_positions()
                    current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                    # Modified: Passed last_action and current_price
                    update_status_json(account_info, positions, daily_stats, current_price, last_action)
                    time.sleep(30)
                    continue

                log_action("Fetching daily data for long-term trend analysis...")
                daily_df = get_daily_data_for_sma(settings.GLOBAL_STOCK_TICKER)
                if daily_df.empty or len(daily_df) < 200:
                    log_action("Insufficient daily data for 200-day SMA. Skipping.")
                    positions = api.list_positions()
                    current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                    # Modified: Passed last_action and current_price
                    update_status_json(account_info, positions, daily_stats, current_price, last_action)
                    time.sleep(30)
                    continue
                
                sma_200 = SMAIndicator(close=daily_df['close'], window=200).sma_indicator().iloc[-1]
                
                log_action("Fetching intraday data for immediate signals...")
                intraday_df = get_latest_intraday_data(settings.GLOBAL_STOCK_TICKER)
                
                latest_features_series = calculate_features(intraday_df)

                if latest_features_series is None:
                    log_action("Failed to calculate features. Skipping.")
                    positions = api.list_positions()
                    current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                    # Modified: Passed last_action and current_price
                    update_status_json(account_info, positions, daily_stats, current_price, last_action)
                    time.sleep(30)
                    continue
                
                log_action(f"--- Latest Feature Data ---\n{latest_features_series.to_string()}\n---------------------------")

                current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                if current_price is None:
                    log_action("Could not fetch live price from Alpaca. Skipping.")
                    positions = api.list_positions()
                    # Modified: Passed last_action and current_price
                    update_status_json(account_info, positions, daily_stats, current_price, last_action)
                    time.sleep(30)
                    continue

                log_action(f"Current live price: ${current_price:.2f}")

                positions = api.list_positions()

                # --- Buy Logic ---
                if not positions:
                    if daily_stats['trades'] >= settings.MAX_TRADES_PER_DAY:
                        log_action(f"Daily trade limit reached. No more trades today.")
                        # Modified: Passed last_action and current_price
                        update_status_json(account_info, positions, daily_stats, current_price, last_action)
                        time.sleep(30)
                        continue
                    
                    features_for_prediction_df = pd.DataFrame([latest_features_series])
                    features_for_prediction_df = features_for_prediction_df[settings.MODEL_FEATURE_NAMES]
                    prediction = final_model.predict(features_for_prediction_df)[0]
                    
                    is_model_bullish = prediction == 1
                    
                    is_indicators_bullish = (
                        (latest_features_series['macd_line'] > latest_features_series['macd_signal']) and
                        (latest_features_series['rsi_14'] < 70) and
                        (latest_features_series['momentum_10d'] > 0)
                    )

                    is_in_uptrend = latest_features_series['close'] > sma_200
                    log_action(f"Trend Check: Close: {latest_features_series['close']:.2f}, SMA200: {sma_200:.2f}. Uptrend: {is_in_uptrend}")

                    is_volatility_normal = True 
                    try:
                        temp_atr = average_true_range(
                            high=intraday_df['high'], low=intraday_df['low'], close=intraday_df['close'], window=14
                        )
                        atr_20_avg = temp_atr.rolling(window=20).mean().iloc[-1]
                        
                        if not pd.isna(atr_20_avg) and 'atr_14' in latest_features_series:
                            current_atr = latest_features_series['atr_14']
                            is_volatility_normal = (current_atr > atr_20_avg * 0.8) and (current_atr < atr_20_avg * 1.5)
                            log_action(f"Volatility Check: Current ATR: {current_atr:.4f}, Avg ATR: {atr_20_avg:.4f}. Normal: {is_volatility_normal}")
                        else:
                            log_action("Could not calculate 20-period ATR average. Volatility check skipped.")
                    except (IndexError, KeyError):
                        log_action("Insufficient data for ATR average. Volatility check skipped.")
                        
                    avg_vol = intraday_df['volume'].tail(5).mean()

                    buy_signal = (is_model_bullish or is_indicators_bullish) and is_in_uptrend and is_volatility_normal and (latest_features_series['volume'] > avg_vol)

                    buy_reason = "No signal"
                    if buy_signal:
                        if is_model_bullish and is_indicators_bullish:
                            buy_reason = "Model and Strong Technical Indicators"
                        elif is_model_bullish:
                            buy_reason = "Model Prediction"
                        elif is_indicators_bullish:
                            buy_reason = "Strong Technical Indicators"

                    if buy_signal:
                        log_action(f"BUY signal received. Reason: {buy_reason}. Calculating position size...")
                        
                        account_info = api.get_account()
                        total_equity = float(account_info.equity)
                        
                        risk_amount = total_equity * settings.RISK_PER_TRADE_PERCENT
                        stop_loss_distance_per_share = latest_features_series['atr_14'] * 10 * settings.SL_MULTIPLIER 
                        
                        if stop_loss_distance_per_share <= 0:
                            log_action("Warning: Stop-loss distance is zero or negative. Cannot calculate shares. Using a fixed distance.")
                            stop_loss_distance_per_share = current_price * 0.01

                        calculated_shares = int(risk_amount / stop_loss_distance_per_share)
                        log_action(f"Dynamic risk calculation: Risk ${risk_amount:.2f} / SL Dist ${stop_loss_distance_per_share:.2f} = {calculated_shares} shares.")

                        max_dollar_amount_per_trade = total_equity * settings.MAX_EQUITY_PER_TRADE
                        max_shares_by_cap = int(max_dollar_amount_per_trade / current_price) if current_price > 0 else 0
                        max_shares_by_cash = int(float(account_info.cash) / current_price) if current_price > 0 else 0

                        shares_to_buy = min(calculated_shares, max_shares_by_cap, max_shares_by_cash)
                        
                        if shares_to_buy > 0:
                            log_action(f"Final shares to buy after capping: {shares_to_buy} shares.")
                            try:
                                api.submit_order(
                                    symbol=settings.GLOBAL_STOCK_TICKER,
                                    qty=shares_to_buy,
                                    side='buy',
                                    type='market',
                                    time_in_force='day'
                                )
                                daily_stats['trades'] += 1
                                last_action = "Buy" # Added: Update last_action
                                log_action(f"BUY executed for {shares_to_buy} shares at ${current_price:.2f}.")
                                last_trade_date = now.date()
                            except Exception as e:
                                log_action(f"API error during buy order: {e}")
                        else:
                            log_action("Calculated shares to buy is zero. Not enough capital or risk parameters too tight.")
                    else:
                        log_action(f"No strong buy signal. Bot remains patient. Prediction: {prediction}.")

                # --- Sell Logic ---
                # --- Sell Logic (المعدل للأمان وحجز الأرباح) ---
                else:
                    position = positions[0]
                    entry_price = float(position.avg_entry_price)
                    qty_to_close = float(position.qty)
                    
                    # جلب الـ ATR أو استخدام قيمة افتراضية للأمان
                    atr_value = latest_features_series.get('atr_14', 0.50)
                    if pd.isna(atr_value): atr_value = 0.50

                    current_profit_pct = ((current_price - entry_price) / entry_price) * 100
                    highest_profit_pct = max(highest_profit_pct, current_profit_pct)

                    # 1. حساب الأهداف (بناءً على الـ Multipliers الجديدة في settings)
                    # الـ Stop Loss الأساسي
                    initial_stop_price = entry_price - (atr_value * settings.SL_MULTIPLIER)
                    # هدف جني الأرباح (Take Profit)
                    take_profit_price = entry_price + (atr_value * settings.TP_MULTIPLIER)

                    # 2. نظام تأمين "نقطة التعادل" (Break-even)
                    # لو السعر طلع وحقق ربح 0.1%، الستوب لوز بيتحرك لـ فوق سعر الدخول بسنة
                    trailing_stop_price = initial_stop_price
                    if current_profit_pct >= 0.10:
                        breakeven_price = entry_price + (atr_value * 0.1) 
                        # التريلينج ستوب الجديد هو السعر اللي يضمن إننا منخسرش
                        trailing_stop_price = max(initial_stop_price, breakeven_price)

                    log_action(f"Position: P&L: {current_profit_pct:.2f}%, Trail SL: ${trailing_stop_price:.2f}, TP: ${take_profit_price:.2f}")

                    # 3. اتخاذ قرار البيع
                    sell_reason = None
                    
                    if current_price >= take_profit_price:
                        sell_reason = "Target Reached (Take Profit)"
                    elif current_price <= trailing_stop_price:
                        sell_reason = "Stop Loss/Breakeven Hit (Safety Exit)"
                    elif current_profit_pct > 0.05 and final_model.predict(pd.DataFrame([latest_features_series])[settings.MODEL_FEATURE_NAMES])[0] == 0:
                        sell_reason = "Model Flip (Exit with small profit)"

                    if sell_reason:
                        log_action(f"SELL signal: {sell_reason}. Closing at ${current_price:.2f}.")
                        try:
                            api.close_position(settings.GLOBAL_STOCK_TICKER)
                            log_action("Position closed successfully.")
                            
                            pl = (current_price - entry_price) * qty_to_close
                            if pl >= 0:
                                daily_stats['wins'] += 1
                                daily_stats['total_profit'] += pl
                            else:
                                daily_stats['losses'] += 1
                                daily_stats['total_loss'] += pl
                            
                            last_action = "Sell"
                            highest_profit_pct = 0.0 
                        except Exception as e:
                            log_action(f"API error during sell order: {e}")
            except KeyboardInterrupt:
                log_action("Trading system stopped by the user.")
                try:
                    api = tradeapi.REST(settings.API_KEY, settings.API_SECRET, settings.BASE_URL, api_version='v2')
                    account_info_eod = api.get_account()
                    end_of_day_equity = float(account_info_eod.equity)
                except Exception:
                    end_of_day_equity = daily_stats.get('daily_high_equity', 0.0)
                
                if daily_stats['trades'] > 0:
                    log_daily_summary(daily_stats, end_of_day_equity)
                    generate_performance_dashboard()
                
                positions = api.list_positions()
                current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                # Modified: Passed last_action and current_price
                update_status_json(account_info_eod, positions, daily_stats, current_price, last_action)
                raise
            except Exception as e:
                log_action(f"A fatal error occurred in the trading loop: {e}")
                traceback.print_exc()
                log_action("The script will attempt to recover in the next cycle.")
            finally:
                log_action("--- Cycle End ---")
                try:
                    account_info = api.get_account()
                    positions = api.list_positions()
                    current_price = get_latest_price_from_alpaca(api, settings.GLOBAL_STOCK_TICKER)
                    # Modified: Passed last_action and current_price
                    update_status_json(account_info, positions, daily_stats, current_price, last_action)
                except Exception as e:
                    log_action(f"Error during final JSON update: {e}")
                time.sleep(30)