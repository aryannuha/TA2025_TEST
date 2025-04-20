# Author: Ammar Aryan Nuha
# Deklarasi library yang digunakan
from flask import Flask, render_template, redirect, url_for, request, get_flashed_messages, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import dash
import dash_bootstrap_components as dbc
import secrets
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.graph_objects as go
import threading
import requests
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from pages.mcs_dashboard_all import main_dashboard_layout, main_dashboard_path
from pages.co2 import co2_layout
from pages.th_in import th_in_layout
from pages.th_out import th_out_layout  
from pages.par import par_layout    
from pages.windspeed import windspeed_layout    
from pages.rainfall import rainfall_layout  

# Initialize Flask app
server = Flask(__name__)
server.secret_key = secrets.token_hex(32)  # Generates a 64-character hexadecimal key

# Menyimpan daftar halaman multipage
pages = {
    main_dashboard_path: main_dashboard_layout,
    "/dash/co2": co2_layout,
    "/dash/th-in": th_in_layout,
    "/dash/th-out": th_out_layout,
    "/dash/par": par_layout,
    "/dash/windspeed": windspeed_layout,
    "/dash/rainfall": rainfall_layout,
}

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)

# User data for simplicity (use a database in production)
users = {'admin': {'password': 'admin'}}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Flask routes
@server.route('/')
def home():
    return redirect(url_for('login'))

@server.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        
        # Tambahkan flash & redirect untuk POST-REDIRECT-GET
        flash('Invalid credentials')
        return redirect(url_for('login'))

    return render_template('login.html')


@server.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user.id)

# @server.route('/dash/')
# @login_required
# def dash_home():
#     return redirect('/dash/')

@server.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Integrate Dash app
app_dash = dash.Dash(__name__, server=server, url_base_pathname='/dash/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# data storage
data = {'waktu' : [], 'suhu' : [], 'kelembaban' : [], 'co2' : [],
        'windspeed' : [], 'rainfall' : []}

# MQTT Configuration
BROKER = "9a59e12602b646a292e7e66a5296e0ed.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "testing"
PASSWORD = "Testing123"
TOPIC_SUHU = "esp32/suhu"
TOPIC_KELEMBABAN = "esp32/kelembaban"
TOPIC_CO2 = "esp32/co2"
TOPIC_WINDSPEED = "esp32/windspeed"
TOPIC_RAINFALL = "esp32/rainfall"

# MQTT Callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to HiveMQ Broker")
        client.subscribe([(TOPIC_SUHU, 0), (TOPIC_KELEMBABAN, 0),
                          (TOPIC_CO2, 0), (TOPIC_WINDSPEED, 0), (TOPIC_RAINFALL, 0)])  # Subscribe ke topik suhu & kelembaban
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    global data
    # print(f"Received message: {msg.topic} - {msg.payload.decode()}")
    try:
        value = float(msg.payload.decode())
        time = pd.Timestamp.now().strftime('%H:%M:%S')
        if msg.topic == TOPIC_SUHU:
            data['waktu'].append(time)
            data['suhu'].append(value)
        elif msg.topic == TOPIC_KELEMBABAN:
            data['kelembaban'].append(value)
        elif msg.topic == TOPIC_CO2:
            data['co2'].append(value)
        elif msg.topic == TOPIC_WINDSPEED:
            data['windspeed'].append(value)
        elif msg.topic == TOPIC_RAINFALL:
            data['rainfall'].append(value)
        
        if len(data['waktu']) > 20:
            data['waktu'].pop(0)
            data['suhu'].pop(0)
            data['kelembaban'].pop(0)
            data['co2'].pop(0)
            data['windspeed'].pop(0)
            data['rainfall'].pop(0)
    
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# MQTT Client
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

# Jalankan MQTT dalam thread
threading.Thread(target=client.loop_forever, daemon=True).start()

app_dash.layout = html.Div([
    # CSS styles for the app
    html.Link(rel='stylesheet', href='/static/style.css'),

    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content', children=[]),    
])

# Routing berdasarkan URL
@app_dash.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def render_page_content(pathname):
    return pages.get(pathname, html.Div("404 - Page not found"))

# Callback Real Time Trend
@app_dash.callback(
    [Output('suhu-display-indoor', 'children'),
     Output('kelembaban-display-indoor', 'children'),
     Output('co2-display', 'children'),
     Output('windspeed-display', 'children'),
     Output('rainfall-display', 'children'),
     Output('temp-graph', 'figure'),
     Output('humidity-graph', 'figure')],
    [Input('interval', 'n_intervals')]
)
# update dashboard Real Time Trend
def update_dashboard(n):
    suhu = data['suhu'][-1] if len(data['suhu']) == len(data['waktu']) and data['suhu'] else 0
    kelembaban = data['kelembaban'][-1] if len(data['kelembaban']) == len(data['waktu']) and data['kelembaban'] else 0
    co2 = data['co2'][-1] if len(data['co2']) == len(data['waktu']) and data['co2'] else 0
    windspeed = data['windspeed'][-1] if len(data['windspeed']) == len(data['waktu']) and data['windspeed'] else 0
    rainfall = data['rainfall'][-1] if len(data['rainfall']) == len(data['waktu']) and data['rainfall'] else 0

    suhu_display = f" {suhu}°C"
    kelembaban_display = f" {kelembaban}%"
    co2_display = f" {co2}PPM"
    windspeed_display = f" {windspeed}m/s"
    rainfall_display = f" {rainfall}mm"

     # Create temperature figure using your code
    fig_suhu = go.Figure(go.Scatter(x=data['waktu'], y=data['suhu'], mode='lines+markers', name='suhu'))
    fig_suhu.update_layout(
        title='',  # Removed title as it's in the header
        xaxis_title='',
        yaxis_title='Temperature (°C)',
        # margin={'l': 30, 'r': 10, 't': 10, 'b': 30},
        # height=140,
        # paper_bgcolor='rgba(0,0,0,0)',
        # plot_bgcolor='#f8f9fa',
        # xaxis={'showgrid': True, 'gridcolor': '#ddd'},
        # yaxis={'showgrid': True, 'gridcolor': '#ddd'}
    )
    
    # Create humidity figure using your code
    fig_kelembaban = go.Figure(go.Scatter(x=data['waktu'], y=data['kelembaban'], mode='lines+markers', name='kelembaban'))
    fig_kelembaban.update_layout(
        title='',  # Removed title as it's in the header
        xaxis_title='',
        yaxis_title='Humidity (%)',
        # margin={'l': 30, 'r': 10, 't': 10, 'b': 30},
        # height=140,
        # paper_bgcolor='rgba(0,0,0,0)',
        # plot_bgcolor='#f8f9fa',
        # xaxis={'showgrid': True, 'gridcolor': '#ddd'},
        # yaxis={'showgrid': True, 'gridcolor': '#ddd'}
    )
    
    return suhu_display, kelembaban_display, co2_display, windspeed_display, rainfall_display, fig_suhu, fig_kelembaban

# Callbacks for Dash app
@app_dash.callback(
    Output("logout-redirect", "href"),
    Input("logout-button", "n_clicks")
)
def logout_redirect(n_clicks):
    if n_clicks:
        return "/logout"  # Redirects to Flask route
    return None

# Run server
if __name__ == '__main__':
    server.run(debug=True)