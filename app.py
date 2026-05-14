from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pymysql
import os
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'your-rds-endpoint.region.rds.amazonaws.com'),
    'user': os.environ.get('DB_USER', 'admin'),
    'password': os.environ.get('DB_PASSWORD', 'your-password'),
    'database': os.environ.get('DB_NAME', 'webapp_db'),
    'charset': 'utf8mb4',
    'autocommit': True
}

def get_db_connection():
    """Create database connection"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Create emails table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create addresses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS addresses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email_id INT,
                    street_address VARCHAR(500) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    state VARCHAR(50) NOT NULL,
                    zip_code VARCHAR(20) NOT NULL,
                    country VARCHAR(100) DEFAULT 'USA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
                )
            """)
            
        connection.commit()
        logger.info("Database tables initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False
    finally:
        connection.close()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Routes
@app.route('/')
def index():
    """Home page with forms"""
    return render_template('index.html')

@app.route('/submit_email', methods=['POST'])
def submit_email():
    """Submit email address - converted from Lambda handler"""
    try:
        # Get email from form data (similar to Lambda event parsing)
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Email address is required', 'error')
            return redirect(url_for('index'))
        
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('index'))
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection error', 'error')
            return redirect(url_for('index'))
        
        try:
            with connection.cursor() as cursor:
                # Check if email already exists
                cursor.execute("SELECT id, status FROM emails WHERE email = %s", (email,))
                result = cursor.fetchone()
                
                if result:
                    flash(f'Email {email} already exists in database', 'info')
                else:
                    # Insert new email
                    cursor.execute(
                        "INSERT INTO emails (email) VALUES (%s)", 
                        (email,)
                    )
                    flash(f'Email {email} successfully added to database', 'success')
                    
        except Exception as e:
            logger.error(f"Database error: {e}")
            flash('Error saving email to database', 'error')
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"Error processing email submission: {e}")
        flash('An error occurred while processing your request', 'error')
    
    return redirect(url_for('index'))

@app.route('/check_email', methods=['POST'])
def check_email():
    """Check if email exists in database"""
    try:
        email = request.form.get('check_email', '').strip().lower()
        
        if not email:
            flash('Email address is required for checking', 'error')
            return redirect(url_for('index'))
        
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('index'))
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection error', 'error')
            return redirect(url_for('index'))
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, status, created_at FROM emails WHERE email = %s", 
                    (email,)
                )
                result = cursor.fetchone()
                
                if result:
                    flash(f'Email {email} found in database (Status: {result[1]}, Added: {result[2]})', 'success')
                else:
                    flash(f'Email {email} not found in database', 'warning')
                    
        except Exception as e:
            logger.error(f"Database error: {e}")
            flash('Error checking email in database', 'error')
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"Error checking email: {e}")
        flash('An error occurred while checking email', 'error')
    
    return redirect(url_for('index'))

@app.route('/submit_address', methods=['POST'])
def submit_address():
    """Submit address for an email - converted from Lambda handler"""
    try:
        # Get form data
        email = request.form.get('address_email', '').strip().lower()
        street_address = request.form.get('street_address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        country = request.form.get('country', 'USA').strip()
        
        # Validation
        if not all([email, street_address, city, state, zip_code]):
            flash('All address fields are required', 'error')
            return redirect(url_for('index'))
        
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('index'))
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection error', 'error')
            return redirect(url_for('index'))
        
        try:
            with connection.cursor() as cursor:
                # Check if email exists
                cursor.execute("SELECT id FROM emails WHERE email = %s", (email,))
                email_result = cursor.fetchone()
                
                if not email_result:
                    flash(f'Email {email} not found. Please add the email first.', 'error')
                    return redirect(url_for('index'))
                
                email_id = email_result[0]
                
                # Insert address
                cursor.execute("""
                    INSERT INTO addresses (email_id, street_address, city, state, zip_code, country)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (email_id, street_address, city, state, zip_code, country))
                
                flash(f'Address successfully added for {email}', 'success')
                
        except Exception as e:
            logger.error(f"Database error: {e}")
            flash('Error saving address to database', 'error')
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"Error processing address submission: {e}")
        flash('An error occurred while processing your request', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/emails', methods=['GET'])
def api_get_emails():
    """API endpoint to get all emails (RESTful endpoint like Lambda)"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT e.id, e.email, e.status, e.created_at,
                           COUNT(a.id) as address_count
                    FROM emails e
                    LEFT JOIN addresses a ON e.id = a.email_id
                    GROUP BY e.id, e.email, e.status, e.created_at
                    ORDER BY e.created_at DESC
                """)
                results = cursor.fetchall()
                
                emails = []
                for row in results:
                    emails.append({
                        'id': row[0],
                        'email': row[1],
                        'status': row[2],
                        'created_at': row[3].isoformat() if row[3] else None,
                        'address_count': row[4]
                    })
                
                return jsonify({
                    'statusCode': 200,
                    'body': {
                        'emails': emails,
                        'count': len(emails)
                    }
                })
                
        except Exception as e:
            logger.error(f"Database error: {e}")
            return jsonify({'error': 'Database query error'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/view_data')
def view_data():
    """View all stored data"""
    try:
        connection = get_db_connection()
        if not connection:
            flash('Database connection error', 'error')
            return redirect(url_for('index'))
        
        emails_data = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT e.id, e.email, e.status, e.created_at,
                           a.street_address, a.city, a.state, a.zip_code, a.country
                    FROM emails e
                    LEFT JOIN addresses a ON e.id = a.email_id
                    ORDER BY e.created_at DESC, a.id
                """)
                results = cursor.fetchall()
                
                for row in results:
                    emails_data.append({
                        'id': row[0],
                        'email': row[1],
                        'status': row[2],
                        'created_at': row[3],
                        'street_address': row[4],
                        'city': row[5],
                        'state': row[6],
                        'zip_code': row[7],
                        'country': row[8]
                    })
                    
        except Exception as e:
            logger.error(f"Database error: {e}")
            flash('Error retrieving data from database', 'error')
        finally:
            connection.close()
        
        return render_template('view_data.html', emails_data=emails_data)
        
    except Exception as e:
        logger.error(f"Error viewing data: {e}")
        flash('An error occurred while retrieving data', 'error')
        return redirect(url_for('index'))

# Health check endpoint (useful for load balancers)
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            return jsonify({'status': 'healthy', 'database': 'connected'}), 200
        else:
            return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 80)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )
