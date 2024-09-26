from flask import Flask, request, render_template
import pandas as pd
import sqlite3
import plotly.graph_objs as go
from datetime import datetime

app = Flask(__name__)

# Database Initialization
def initialize_database():
    conn = get_db_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS backtest_results (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            derivative TEXT NOT NULL,
                            expiry_date TEXT NOT NULL,
                            timeframes TEXT NOT NULL,
                            strategy TEXT NOT NULL,
                            total_profit REAL NOT NULL,
                            trades INTEGER NOT NULL)''')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(backtest_results);")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'timeframes' not in columns:
            conn.execute('ALTER TABLE backtest_results ADD COLUMN timeframes TEXT;')
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
    finally:
        conn.close()

def get_db_connection():
    conn = sqlite3.connect('sqlite.db')
    conn.row_factory = sqlite3.Row
    return conn

# Data Loading
def load_feather_file(file_path):
    data = pd.read_feather(file_path)
    if 'close' in data.columns:
        data.rename(columns={'close': 'Close'}, inplace=True)
    return data

# Trading Strategies
def moving_average_crossover(data, short_window=5, long_window=20):
    if 'Close' not in data.columns:
        raise ValueError("Close column is missing from the DataFrame")

    data['Short_MA'] = data['Close'].rolling(window=short_window).mean()
    data['Long_MA'] = data['Close'].rolling(window=long_window).mean()

    signals = []
    for i in range(len(data)):
        if pd.isna(data['Short_MA'].iloc[i]) or pd.isna(data['Long_MA'].iloc[i]):
            signals.append('Hold')
        elif data['Short_MA'].iloc[i] > data['Long_MA'].iloc[i]:
            signals.append('Buy')
        elif data['Short_MA'].iloc[i] < data['Long_MA'].iloc[i]:
            signals.append('Sell')
        else:
            signals.append('Hold')
    
    data['Signals'] = signals
    return data

def apply_stop_loss(data, stop_loss_percentage=0.02):
    data['Stop_Loss'] = data['Close'] * (1 - stop_loss_percentage)
    return data

# Backtesting
def backtest(data):
    if 'Signals' not in data.columns:
        raise KeyError("'Signals' column is missing from the DataFrame")

    position = None
    total_profit = 0
    trades = 0

    for i in range(1, len(data)):
        if data['Signals'].iloc[i] == 'Buy' and position is None:
            position = data['Close'].iloc[i]
        elif data['Signals'].iloc[i] == 'Sell' and position is not None:
            total_profit += data['Close'].iloc[i] - position
            trades += 1
            position = None

    return total_profit, trades

# Plotting Results
def plot_results(data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['date'], y=data['Close'], mode='lines', name='Close Price'))

    if 'Short_MA' in data.columns:
        fig.add_trace(go.Scatter(x=data['date'], y=data['Short_MA'], mode='lines', name='Short MA'))
    
    if 'Long_MA' in data.columns:
        fig.add_trace(go.Scatter(x=data['date'], y=data['Long_MA'], mode='lines', name='Long MA'))
    
    fig.update_layout(title='Backtest Results', xaxis_title='Date', yaxis_title='Price')
    return fig.to_html(full_html=False)

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    derivative = request.form['derivative']
    expiry_date = request.form['expiry_date']
    timeframes = request.form.getlist('timeframes')
    strategy = request.form['strategy']

    # Validate and format the expiry date
    if expiry_date:
        try:
            formatted_date = datetime.strptime(expiry_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD.", 400

    if not derivative or not expiry_date or not timeframes:
        return "Invalid input. Please fill out all fields.", 400

    # Load data from the Feather file
    try:
        data = load_feather_file('data/data1.feather')
    except Exception as e:
        return f"Failed to load data: {str(e)}", 500

    # Apply the chosen strategy
    if strategy == 'moving_average_crossover':
        processed_data = moving_average_crossover(data)
    elif strategy == 'stop_loss':
        processed_data = apply_stop_loss(data)
        processed_data['Signals'] = 'Hold'
    else:
        return "Unknown strategy", 400

    # Run backtest
    total_profit, trades = backtest(processed_data)

    # Store results in the database
    try:
        conn = get_db_connection()
        conn.execute('''INSERT INTO backtest_results (derivative, expiry_date, timeframes, strategy, total_profit, trades)
                         VALUES (?, ?, ?, ?, ?, ?)''', (derivative, formatted_date, ','.join(timeframes), strategy, total_profit, trades))
        conn.commit()
    except Exception as e:
        return f"Failed to store results: {str(e)}", 500
    finally:
        conn.close()

    plot_html = plot_results(processed_data)
    return render_template('results.html', derivative=derivative, expiry_date=formatted_date, timeframes=timeframes, strategy=strategy, total_profit=total_profit, trades=trades, plot_html=plot_html)

if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
