import sqlite3
import os

def run_sql_file(filename):
    with open(filename, 'r') as sql_file:
        sql_script = sql_file.read()
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    try:
        cursor.executescript(sql_script)
        conn.commit()
        print(f"Successfully executed {filename}")
    except Exception as e:
        print(f"Error executing {filename}: {str(e)}")
    finally:
        conn.close()

def main():
    # Remove existing database if it exists
    if os.path.exists('inventory.db'):
        os.remove('inventory.db')
        print("Removed existing database")
    
    # Run schema and initial data
    run_sql_file('schema.sql')
    run_sql_file('initial_data.sql')
    
    print("Database setup completed successfully!")

if __name__ == "__main__":
    main() 