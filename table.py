
import sqlite3
def get_db_connection():
    conn = sqlite3.connect('sqlite.db')
    conn.row_factory = sqlite3.Row  # So we can access columns by name
    return conn
def initialize_database():
    conn = get_db_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS backtest_results")
        conn.execute('''CREATE TABLE backtest_results (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            derivative TEXT NOT NULL,
                            expiry_date TEXT NOT NULL,
                            timeframes TEXT NOT NULL,
                            strategy TEXT NOT NULL,
                            total_profit REAL NOT NULL,
                            trades INTEGER NOT NULL,
                            initial_capital REAL NOT NULL,
                            final_capital REAL NOT NULL,
                            backtest_date TEXT NOT NULL,
                            winning_trades INTEGER NOT NULL,
                            losing_trades INTEGER NOT NULL)''')
        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
    finally:
        conn.close()
