from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pymysql
import os
import logging
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file (dev) or system env (prod)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')

# Database configuration — all values come from environment variables
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST'),
    'user':     os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'charset':  'utf8mb4',
    'autocommit': True,
    'connect_timeout': 5,
}

def get_db_connection():
    """Create and return a database connection, or None on failure."""
    missing = [k for k, v in DB_CONFIG.items() if not v and k not in ('autocommit', 'charset', 'connect_timeout')]
    if missing:
        logger.error(f"Missing DB environment variables: {missing}")
        return None
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_database():
    """Create tables if they don't already exist."""
    connection = get_db_connection()
    if not connection:
        logger.warning("Skipping DB init — no connection available.")
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id           INT AUTO_INCREMENT PRIMARY KEY,
                    email        VARCHAR(255) NOT NULL UNIQUE,
                    status       VARCHAR(50)  DEFAULT 'active',
                    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS addresses (
                    id             INT AUTO_INCREMENT PRIMARY KEY,
                    email_id       INT,
                    street_address VARCHAR(500) NOT NULL,
                    city           VARCHAR(100) NOT NULL,
                    state          VARCHAR(50)  NOT NULL,
                    zip_code       VARCHAR(20)  NOT NULL,
                    country        VARCHAR(100) DEFAULT 'USA',
                    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
                )
            """)
        connection.commit()
        logger.info("Database tables initialised successfully.")
        return True
    except Exception as e:
        logger.error(f"Database initialisation error: {e}")
        return False
    finally:
        connection.close()

def validate_email(email):
    """Return True if email matches a basic RFC pattern."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit_email', methods=['POST'])
def submit_email():
    """Add a new email address to the database."""
    email = request.form.get('email', '').strip().lower()

    if not email:
        flash('Email address is required.', 'error')
        return redirect(url_for('index'))
    if not validate_email(email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('index'))

    connection = get_db_connection()
    if not connection:
        flash('Database connection error — check server logs.', 'error')
        return redirect(url_for('index'))

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, status FROM emails WHERE email = %s", (email,))
            result = cursor.fetchone()
            if result:
                flash(f'Email {email} already exists in the database.', 'info')
            else:
                cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
                flash(f'Email {email} added successfully.', 'success')
    except Exception as e:
        logger.error(f"submit_email DB error: {e}")
        flash('Error saving email — check server logs.', 'error')
    finally:
        connection.close()

    return redirect(url_for('index'))


@app.route('/check_email', methods=['POST'])
def check_email():
    """Check whether an email exists in the database."""
    email = request.form.get('check_email', '').strip().lower()

    if not email:
        flash('Email address is required.', 'error')
        return redirect(url_for('index'))
    if not validate_email(email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('index'))

    connection = get_db_connection()
    if not connection:
        flash('Database connection error — check server logs.', 'error')
        return redirect(url_for('index'))

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, status, created_at FROM emails WHERE email = %s", (email,)
            )
            result = cursor.fetchone()
            if result:
                flash(
                    f'Email {email} found — Status: {result[1]}, Added: {result[2]}',
                    'success'
                )
            else:
                flash(f'Email {email} not found in the database.', 'warning')
    except Exception as e:
        logger.error(f"check_email DB error: {e}")
        flash('Error checking email — check server logs.', 'error')
    finally:
        connection.close()

    return redirect(url_for('index'))


@app.route('/submit_address', methods=['POST'])
def submit_address():
    """Associate a physical address with an existing email."""
    email          = request.form.get('address_email', '').strip().lower()
    street_address = request.form.get('street_address', '').strip()
    city           = request.form.get('city', '').strip()
    state          = request.form.get('state', '').strip()
    zip_code       = request.form.get('zip_code', '').strip()
    country        = request.form.get('country', 'USA').strip()

    if not all([email, street_address, city, state, zip_code]):
        flash('All address fields are required.', 'error')
        return redirect(url_for('index'))
    if not validate_email(email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('index'))

    connection = get_db_connection()
    if not connection:
        flash('Database connection error — check server logs.', 'error')
        return redirect(url_for('index'))

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM emails WHERE email = %s", (email,))
            email_result = cursor.fetchone()
            if not email_result:
                flash(f'Email {email} not found. Add the email first.', 'error')
                return redirect(url_for('index'))

            cursor.execute(
                """INSERT INTO addresses
                       (email_id, street_address, city, state, zip_code, country)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (email_result[0], street_address, city, state, zip_code, country)
            )
            flash(f'Address added successfully for {email}.', 'success')
    except Exception as e:
        logger.error(f"submit_address DB error: {e}")
        flash('Error saving address — check server logs.', 'error')
    finally:
        connection.close()

    return redirect(url_for('index'))


@app.route('/api/emails', methods=['GET'])
def api_get_emails():
    """JSON endpoint: all emails with address counts."""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.email, e.status, e.created_at,
                       COUNT(a.id) AS address_count
                FROM   emails e
                LEFT JOIN addresses a ON e.id = a.email_id
                GROUP BY e.id, e.email, e.status, e.created_at
                ORDER BY e.created_at DESC
            """)
            rows = cursor.fetchall()

        emails = [
            {
                'id':            r[0],
                'email':         r[1],
                'status':        r[2],
                'created_at':    r[3].isoformat() if r[3] else None,
                'address_count': r[4],
            }
            for r in rows
        ]
        return jsonify({'statusCode': 200, 'body': {'emails': emails, 'count': len(emails)}})
    except Exception as e:
        logger.error(f"api_get_emails DB error: {e}")
        return jsonify({'error': 'Database query error'}), 500
    finally:
        connection.close()


@app.route('/view_data')
def view_data():
    """Render a table of all stored emails and addresses."""
    connection = get_db_connection()
    if not connection:
        flash('Database connection error — check server logs.', 'error')
        return redirect(url_for('index'))

    emails_data = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.email, e.status, e.created_at,
                       a.street_address, a.city, a.state, a.zip_code, a.country
                FROM   emails e
                LEFT JOIN addresses a ON e.id = a.email_id
                ORDER BY e.created_at DESC, a.id
            """)
            for row in cursor.fetchall():
                emails_data.append({
                    'id':             row[0],
                    'email':          row[1],
                    'status':         row[2],
                    'created_at':     row[3],
                    'street_address': row[4],
                    'city':           row[5],
                    'state':          row[6],
                    'zip_code':       row[7],
                    'country':        row[8],
                })
    except Exception as e:
        logger.error(f"view_data DB error: {e}")
        flash('Error retrieving data — check server logs.', 'error')
    finally:
        connection.close()

    return render_template('view_data.html', emails_data=emails_data)


@app.route('/health')
def health_check():
    """Health check — useful for ALB/ELB target-group checks."""
    connection = get_db_connection()
    if connection:
        connection.close()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503


# ---------------------------------------------------------------------------
# Entry point (development only — Apache uses webapp.wsgi in production)
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    init_database()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true',
    )
