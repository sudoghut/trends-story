import sqlite3

def create_database(db_name):

    # Connect to SQLite database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create the serpapi_data table
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
    
    # Create the main_news_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS main_news_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news TEXT,
            date TEXT,
            serpapi_id INTEGER,
            image_id INTEGER,
            CONSTRAINT fk_news_serpapi_id FOREIGN KEY (serpapi_id) REFERENCES serpapi_data (id) ON DELETE CASCADE,
            CONSTRAINT fk_news_image_id FOREIGN KEY (image_id) REFERENCES image_data (id) ON DELETE CASCADE
        )
    ''')

    # Create the image_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT
        )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database and table created successfully!")

if __name__ == "__main__":
    create_database("trends_data.db")