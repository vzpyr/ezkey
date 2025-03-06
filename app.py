from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
import random
import string

admin_password = ""

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///licenses.db'

db = SQLAlchemy(app)

class LicenseKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(32), unique=True, nullable=False)
    uses_left = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="invalid password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@requires_auth
def index():
    licenses = LicenseKey.query.all()
    return render_template('admin.html', licenses=licenses)

@app.route('/create-license', methods=['POST'])
@requires_auth
def create_license():
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=4))
    part2 = ''.join(random.choices(chars, k=4))
    license_key = LicenseKey(
        key=f"{part1}-{part2}",
        uses_left=int(request.form['uses']),
        expiry_date=datetime.strptime(request.form['expiry date'], '%Y-%m-%d')
    )
    db.session.add(license_key)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete-license/<int:id>', methods=['POST'])
@requires_auth
def delete_license(id):
    license_key = LicenseKey.query.get_or_404(id)
    db.session.delete(license_key)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/verify', methods=['POST'])
def verify():
    key = request.json.get('key')
    if not key:
        return jsonify({"valid": False, "message": "no key provided"})
    license_key = LicenseKey.query.filter_by(key=key).first()
    if not license_key:
        return jsonify({"valid": False, "message": "invalid key"})
    if license_key.expiry_date < datetime.utcnow():
        db.session.delete(license_key)
        db.session.commit()
        return jsonify({"valid": False, "message": "expired key"})
    if license_key.uses_left <= 0:
        db.session.delete(license_key)
        db.session.commit()
        return jsonify({"valid": False, "message": "expired key"})
    license_key.uses_left -= 1
    db.session.commit()
    return jsonify({
        "valid": True,
        "uses_left": license_key.uses_left,
        "expiration": int(license_key.expiry_date.timestamp())
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
