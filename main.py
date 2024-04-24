from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)
uri = os.getenv("DATABASE_URL")  # Retrieve the URI from the environment variable
#if uri.startswith("postgres://"):
#    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # Updated size for IPv6 compatibility
    user_agent = db.Column(db.String(256))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    vpn = db.Column(db.String(45))
    proxy = db.Column(db.String(45))
    tor = db.Column(db.String(45))
    first_vote = db.Column(db.String(128))
    second_vote = db.Column(db.String(128))

with app.app_context():
    db.create_all()

def get_ip_details(ip):
    """Retrieve IP details including security and location data."""
    api_key = os.getenv('VPNAPI_KEY', 'YOUR_API_KEY')
    try:
        response = requests.get(f'https://vpnapi.io/api/{ip}?key={api_key}')
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f'Failed to retrieve IP details: {e}')
        return None

@app.route('/', methods=['GET', 'POST'])
def home():
    error = None
    if request.method == 'POST':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        ip_details = get_ip_details(ip)

        if ip_details is None:
            error = "Nie udało się uzyskać informacji o IP."
            return render_template('home.html', error=error)

        if ip_details['security']['vpn'] or ip_details['security']['proxy'] or ip_details['security']['tor']:
            return "Korzystasz z VPN/proxy/TOR. Nie możesz zagłosować w tej ankiecie. Jeżeli chcesz zagłosować - wyłącz VPN/proxy/TOR."

        user_agent = request.user_agent.string
        first_vote = request.form['first_vote']
        second_vote = request.form['second_vote']

        recent_vote = Vote.query.filter(
            Vote.ip_address == ip,
            Vote.timestamp > datetime.utcnow() - timedelta(hours=24)
        ).order_by(Vote.timestamp.desc()).first()

        if recent_vote:
            next_vote_time = recent_vote.timestamp + timedelta(hours=24)
            return f"Już mam Twój głos ;) Możesz zagłosować ponownie {next_vote_time.strftime('%Y-%m-%d %H:%M:%S')}."

        country = ip_details['location'].get('country', 'Unknown')
        city = ip_details['location'].get('city', 'Unknown')
        vpn = ip_details['security'].get('vpn', 'Unknown')
        proxy = ip_details['security'].get('proxy', 'Unknown')
        tor = ip_details['security'].get('tor', 'Unknown')

        new_vote = Vote(ip_address=ip, user_agent=user_agent, country=country, city=city,
                        vpn=vpn, proxy=proxy, tor=tor, first_vote=first_vote, second_vote=second_vote)
        db.session.add(new_vote)
        db.session.commit()
        return redirect(url_for('thanks'))

    return render_template('home.html', error=error)


@app.route('/thanks')
def thanks():
    return "Dziękuję za Twój głos!"

if __name__ == '__main__':
    app.run(debug=True)