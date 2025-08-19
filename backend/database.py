import sqlite3
from datetime import datetime
import logging

DB_PATH = "ocpp_logs.db"

# db functions for help :(
def get_db_connection(): #connection to db
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) #to get different threats at the same time
    conn.row_factory = sqlite3.Row #read as dict
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS charge_points (
            cp_id TEXT PRIMARY KEY,
            vendor TEXT,
            model TEXT,
            status TEXT,
            last_seen TIMESTAMP,
            busy INTEGER DEFAULT 0,
            last_heartbeat TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cp_id TEXT, status TEXT, timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cp_id TEXT, timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS boot_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cp_id TEXT, vendor TEXT, model TEXT, timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()