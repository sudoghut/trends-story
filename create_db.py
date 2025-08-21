import sqlite3

def create_database():
    # Connect to SQLite database (creates file if it doesn't exist)
    conn = sqlite3.connect('trends_data.db')
    cursor = conn.cursor()
    
    # Create the data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS serpapi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            start_timestamp TEXT,
            active BOOLEAN,
            search_volume INTEGER,
            increase_percentage INTEGER,
            categories TEXT,
            trend_breakdown TEXT,
            serpapi_google_trends_link TEXT,
            news_page_token TEXT,
            serpapi_news_link TEXT,
            date TEXT
        )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database and table created successfully!")

if __name__ == "__main__":
    create_database()