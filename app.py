# Author: Ammar Aryan Nuha
# Deklarasi library yang digunakan
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import dash
import pytz
import dash_bootstrap_components as dbc
import secrets
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import threading
import ssl
import random
import pandas as pd
import numpy as np
from scipy import interpolate
from datetime import datetime
from dash import dcc, html
from dash.dependencies import Input, Output
from pages.mcs_dashboard_all import main_dashboard_layout, main_dashboard_path
from pages.co2 import co2_layout
from pages.th_in import th_in_layout
from pages.th_out import th_out_layout  
from pages.par import par_layout    
from pages.windspeed import windspeed_layout    
from pages.rainfall import rainfall_layout  
from pages.alarm import alarm_layout  
from pages.gps import gps_layout  
from engineer_pages.mcs_dashboard_eng import engineer_dashboard_layout
from engineer_pages.co2_eng import engineer_co2_layout
from engineer_pages.th_in_eng import engineer_th_in_layout
from engineer_pages.th_out_eng import engineer_th_out_layout  
from engineer_pages.par_eng import engineer_par_layout    
from engineer_pages.windspeed_eng import engineer_windspeed_layout    
from engineer_pages.rainfall_eng import engineer_rainfall_layout  
from engineer_pages.alarm_eng import engineer_alarm_layout  
from engineer_pages.gps_eng import engineer_gps_layout  

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
    "/dash/alarm": alarm_layout,
    "/dash/gps": gps_layout,
}

engineer_pages = {
    "/dash/engineer/": engineer_dashboard_layout,
    "/dash/engineer/co2": engineer_co2_layout,
    "/dash/engineer/th-in": engineer_th_in_layout,
    "/dash/engineer/th-out": engineer_th_out_layout,
    "/dash/engineer/par": engineer_par_layout,
    "/dash/engineer/windspeed": engineer_windspeed_layout,
    "/dash/engineer/rainfall": engineer_rainfall_layout,
    "/dash/engineer/alarm": engineer_alarm_layout,
    "/dash/engineer/gps": engineer_gps_layout,
}

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = 'login'  # Specify the login route

# User data for simplicity (use a database in production)
users = {'engineer': {'password': 'engineer'}}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Flask routes
@server.route('/')
def home():
    # Public home page, redirects to guest dashboard
    return redirect('/dash/')

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

@server.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')  # Redirect to public home page
# end of flask route

# Integrate Dash app
app_dash = dash.Dash(__name__, server=server, url_base_pathname='/dash/', external_stylesheets=[dbc.themes.BOOTSTRAP], title='MCS Dashboard', suppress_callback_exceptions=True)
 
@app_dash.server.before_request
def restrict_dash_pages():
    if request.path.startswith('/dash/engineer') and not session.get('_user_id'):
        return redirect(url_for('login'))

# data storage
data = {
    'waktu': [],      # Time values
    'kodeDataSuhuIn': [],       # Temperature values 
    'kodeDataKelembabanIn': [], # Humidity values
    'kodeDataSuhuOut': [],   # Outdoor temperature values
    'kodeDataKelembabanOut': [], # Outdoor humidity values
    'kodeDataCo2': [],        # CO2 values
    'kodeDataWindspeed': [],  # Wind speed values
    'kodeDataRainfall': [],    # Rainfall values
    'kodeDataPar': [],    # PAR values
    'kodeDataLat': [],   # Latitude values
    'kodeDataLon': []    # Longitude values
}

# Define some locations in Bandung, Indonesia for demonstration
LOCATIONS = [
    {"name": "Bandung City Square", "lat": -6.921151, "lon": 107.607301},
    {"name": "Gedung Sate", "lat": -6.902454, "lon": 107.618881},
    {"name": "Dago Street", "lat": -6.893702, "lon": 107.613251},
    {"name": "Bandung Station", "lat": -6.914744, "lon": 107.602458},
    {"name": "Paris Van Java Mall", "lat": -6.888771, "lon": 107.595337}
]

# Coordinates for a device path simulation
def generate_path_points(center_lat, center_lon, points=10, radius=0.005):
    """Generate a path of points around a center location"""
    path = []
    for i in range(points):
        # Create a small random deviation
        lat_offset = radius * np.cos(i * 2 * np.pi / points)
        lon_offset = radius * np.sin(i * 2 * np.pi / points)
        
        # Add small random noise
        lat_noise = random.uniform(-0.0005, 0.0005)
        lon_noise = random.uniform(-0.0005, 0.0005)
        
        path.append({
            "lat": center_lat + lat_offset + lat_noise,
            "lon": center_lon + lon_offset + lon_noise
        })
    return path

# Generate a sample path
PATH_POINTS = generate_path_points(-6.914744, 107.609810, points=20)

# MQTT Configuration
BROKER = "9a59e12602b646a292e7e66a5296e0ed.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "testing"
PASSWORD = "Testing123"

# Create SSL/TLS context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# TOPIC = "esp32/+/+"  # Subscribe to all topics under esp32
TOPIC_SUHU = "mcs/kodeDataSuhuIn"
TOPIC_KELEMBABAN = "mcs/kodeDataKelembabanIn"
TOPIC_SUHU_OUT = "mcs/kodeDataSuhuOut"
TOPIC_KELEMBABAN_OUT = "mcs/kodeDataKelembabanOut"
TOPIC_CO2 = "mcs/kodeDataCo2"
TOPIC_WINDSPEED = "mcs/kodeDataWindspeed"
TOPIC_RAINFALL = "mcs/kodeDataRainfall"
TOPIC_PAR = "mcs/kodeDataPar"
TOPIC_LAT = "mcs/kodeDataLat"
TOPIC_LON = "mcs/kodeDataLon"

# MQTT Callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to HiveMQ Broker")
        client.subscribe([(TOPIC_SUHU, 0), (TOPIC_KELEMBABAN, 0),
                          (TOPIC_SUHU_OUT, 0), (TOPIC_KELEMBABAN_OUT, 0),
                          (TOPIC_CO2, 0), (TOPIC_WINDSPEED, 0), 
                          (TOPIC_RAINFALL, 0), (TOPIC_PAR, 0),
                         (TOPIC_LAT, 0), (TOPIC_LON, 0)])  # Subscribe ke topik suhu & kelembaban
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    global data
    try:
        topic = msg.topic.split('/')[-1]  # Get the last part of the topic (e.g., 'suhu' from 'esp32/suhu')
        payload = float(msg.payload.decode())
        
        current_time = datetime.now(tz=pytz.timezone('Asia/Jakarta')).strftime('%H:%M:%S')
        
        # Initialize lists if they don't exist
        if topic in ['kodeDataSuhuIn', 'kodeDataKelembabanIn', 'kodeDataSuhuOut', 'kodeDataKelembabanOut',
                      'kodeDataCo2', 'kodeDataWindspeed', 'kodeDataRainfall', 'kodeDataPar',
                    'kodeDataLat', 'kodeDataLon']:
            if len(data[topic]) >= 20:  # Keep only last 20 points
                data[topic] = data[topic][1:]
            data[topic].append(payload)
            
            # Keep waktu list in sync with the latest data addition
            # This ensures all lists have the same length
            if topic == 'kodeDataSuhuIn':  # Only update waktu when temperature data comes in
                if len(data['waktu']) >= 20:
                    data['waktu'] = data['waktu'][1:]
                data['waktu'].append(current_time)

    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# MQTT Client
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set_context(ssl_context)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

# Jalankan MQTT dalam thread
threading.Thread(target=client.loop_forever, daemon=True).start()

# main layout dash
app_dash.layout = html.Div([
    # CSS styles for the app
    html.Link(rel='stylesheet', href='/static/style.css'),

    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content', children=[]),    
])

# Callback Routing berdasarkan URL
@app_dash.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    # Check if it's an engineer path
    if pathname.startswith('/dash/engineer/'):
        # Verify user is authenticated
        if not current_user.is_authenticated:
            return html.Div([
                html.H3('Access Denied'),
                html.P('Please log in as an engineer to access this page.'),
                html.A('Login', href='/login', className='btn btn-primary')
            ])
        # Show engineer page if authenticated
        if pathname in engineer_pages:
            return engineer_pages[pathname]
        # 404 for invalid engineer paths
        return html.Div([
            html.H3('404: Page not found'),
            html.A('Go to engineer dashboard', href='/dash/engineer/')
        ])
    
    # For guest paths (no authentication needed)
    if pathname in pages:
        return pages[pathname]
    
    # Default to guest homepage for unknown paths
    return pages['/dash/']

# Callback for main dashboard
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'suhu-display-indoor'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'kelembaban-display-indoor'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'suhu-display-outdoor'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'kelembaban-display-outdoor'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'co2-display'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'windspeed-display'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'rainfall-display'}, 'children'),
     Output({'type': 'sensor-value', 'id': 'par-display'}, 'children')],
    [Input('interval_mcs', 'n_intervals')]
)
def update_main_dashboard(n):
    try:
        suhu = data['kodeDataSuhuIn'][-1] if data['kodeDataSuhuIn'] else 0
        kelembaban = data['kodeDataKelembabanIn'][-1] if data['kodeDataKelembabanIn'] else 0
        suhu_out = data['kodeDataSuhuOut'][-1] if data['kodeDataSuhuOut'] else 0
        kelembaban_out = data['kodeDataKelembabanOut'][-1] if data['kodeDataKelembabanOut'] else 0
        co2 = data['kodeDataCo2'][-1] if data['kodeDataCo2'] else 0
        windspeed = data['kodeDataWindspeed'][-1] if data['kodeDataWindspeed'] else 0
        rainfall = data['kodeDataRainfall'][-1] if data['kodeDataRainfall'] else 0
        par = data['kodeDataPar'][-1] if data['kodeDataPar'] else 0

        return (
            f" {suhu}°C",
            f" {kelembaban}%",
            f" {suhu_out}°C",
            f" {kelembaban_out}%",
            f" {co2}PPM",
            f" {windspeed}m/s",
            f" {rainfall}mm",
            f" {par}μmol/m²/s"
        )
    except Exception as e:
        print(f"Error in update_main_dashboard: {e}")
        return "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"

# Separate callback for th_in layout - Completely revised version
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'suhu-display-indoor'}, 'children', allow_duplicate=True),
     Output({'type': 'sensor-value', 'id': 'kelembaban-display-indoor'}, 'children', allow_duplicate=True),
     Output('temp-graph', 'figure'),
     Output('humidity-graph', 'figure')],
    [Input('interval_thin', 'n_intervals')],
    prevent_initial_call=True
)
def update_th_in_dashboard(n):
    try:        
        # Default values
        suhu_value = "N/A"
        kelembaban_value = "N/A"
        
        # Empty figures with proper layout
        empty_temp_fig = go.Figure(layout=dict(
            title="Temperature Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Temperature (°C)", range=[0, 40]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=150,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        empty_humid_fig = go.Figure(layout=dict(
            title="Humidity Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Humidity (%)", range=[40, 100]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=150,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        # Check if we have data
        if not data['kodeDataSuhuIn'] or not data['kodeDataKelembabanIn'] or not data['waktu']:
            return suhu_value, kelembaban_value, empty_temp_fig, empty_humid_fig
        
        # Get the latest values
        suhu = data['kodeDataSuhuIn'][-1] if data['kodeDataSuhuIn'] else 0
        kelembaban = data['kodeDataKelembabanIn'][-1] if data['kodeDataKelembabanIn'] else 0
        suhu_value = f"{suhu}°C"
        kelembaban_value = f"{kelembaban}%"
        
        # Create temperature graph with properly aligned x and y values
        temp_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataSuhuIn']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataSuhuIn']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataSuhuIn'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                temp_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#FF4B4B', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                temp_fig.update_layout(
                    title="Temperature Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="Temperature (°C)", range=[0, 40]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=150,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                temp_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#FF4B4B', width=3),
                    showlegend=False
                ))
                temp_fig.update_layout(
                    title="Temperature Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Temperature (°C)", range=[0, 40]),
                    height=150,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating temp graph: {e}")
            # Create a basic empty chart if there's an error
            temp_fig = go.Figure()
            temp_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )

        # Create humidity graph with properly aligned x and y values
        humid_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataKelembabanIn']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataKelembabanIn']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataKelembabanIn'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                humid_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                humid_fig.update_layout(
                    title="Humidity Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="Humidity (%)", range=[40, 100]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=150,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                humid_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#4B86FF', width=3),
                    showlegend=False
                ))
                humid_fig.update_layout(
                    title="Humidity Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Humidity (%)", range=[40, 100]),
                    height=150,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating humid graph: {e}")
            # Create a basic empty chart if there's an error
            humid_fig = go.Figure()
            humid_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        return suhu_value, kelembaban_value, temp_fig, humid_fig
    
    except Exception as e:
        print(f"Error in update_th_in_dashboard: {e}")
        # Return default values if there's an error
        default_fig = go.Figure(layout=dict(
            title="Data Unavailable",
            annotations=[dict(
                text="Error loading data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )]
        ))
        return "N/A", "N/A", default_fig, default_fig
    
# Separate callback for th_out layout - Completely revised version
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'suhu-display-outdoor'}, 'children', allow_duplicate=True),
     Output({'type': 'sensor-value', 'id': 'kelembaban-display-outdoor'}, 'children', allow_duplicate=True),
     Output('temp-graph-out', 'figure'),
     Output('humidity-graph-out', 'figure')],
    [Input('interval_thout', 'n_intervals')],
    prevent_initial_call=True
)
def update_th_out_dashboard(n):
    try:        
        # Default values
        suhu_value = "N/A"
        kelembaban_value = "N/A"
        
        # Empty figures with proper layout
        empty_temp_fig = go.Figure(layout=dict(
            title="Temperature Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Temperature (°C)", range=[0, 40]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=150,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        empty_humid_fig = go.Figure(layout=dict(
            title="Humidity Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Humidity (%)", range=[40, 100]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=150,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        # Check if we have data
        if not data['kodeDataSuhuOut'] or not data['kodeDataKelembabanOut'] or not data['waktu']:
            return suhu_value, kelembaban_value, empty_temp_fig, empty_humid_fig
        
        # Get the latest values
        suhu = data['kodeDataSuhuOut'][-1] if data['kodeDataSuhuOut'] else 0
        kelembaban = data['kodeDataKelembabanOut'][-1] if data['kodeDataKelembabanOut'] else 0
        suhu_value = f"{suhu}°C"
        kelembaban_value = f"{kelembaban}%"

        # Create temperature graph with properly aligned x and y values
        temp_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataSuhuOut']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataSuhuOut']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataSuhuOut'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                temp_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#FF4B4B', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                temp_fig.update_layout(
                    title="Temperature Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="Temperature (°C)", range=[0, 40]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=150,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                temp_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#FF4B4B', width=3),
                    showlegend=False
                ))
                temp_fig.update_layout(
                    title="Temperature Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Temperature (°C)", range=[0, 40]),
                    height=150,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating temp graph: {e}")
            # Create a basic empty chart if there's an error
            temp_fig = go.Figure()
            temp_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )

        # Create humidity graph with properly aligned x and y values
        humid_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataKelembabanOut']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataKelembabanOut']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataKelembabanOut'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                humid_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                humid_fig.update_layout(
                    title="Humidity Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="Humidity (%)", range=[40, 100]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=150,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                humid_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#4B86FF', width=3),
                    showlegend=False
                ))
                humid_fig.update_layout(
                    title="Humidity Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Humidity (%)", range=[40, 100]),
                    height=150,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating humid graph: {e}")
            # Create a basic empty chart if there's an error
            humid_fig = go.Figure()
            humid_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        return suhu_value, kelembaban_value, temp_fig, humid_fig
    
    except Exception as e:
        print(f"Error in update_th_in_dashboard: {e}")
        # Return default values if there's an error
        default_fig = go.Figure(layout=dict(
            title="Data Unavailable",
            annotations=[dict(
                text="Error loading data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )]
        ))
        return "N/A", "N/A", default_fig, default_fig
    
# Separate callback for windspeed layout - Completely revised version
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'windspeed-display'}, 'children', allow_duplicate=True),
     Output('windspeed-graph', 'figure')],
    [Input('interval_windspeed', 'n_intervals')],
    prevent_initial_call=True
)
def update_windspeed_dashboard(n):
    try:        
        # Default values
        windspeed_value = "N/A"
        
        # Empty figures with proper layout
        empty_windspeed_fig = go.Figure(layout=dict(
            title="Windspeed Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Windspeed (m/s)", range=[0, 70]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=300,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        # Check if we have data
        if not data['kodeDataWindspeed'] or not data['waktu']:
            return windspeed_value, empty_windspeed_fig
        
        # Get the latest values
        windspeed = data['kodeDataWindspeed'][-1] if data['kodeDataWindspeed'] else 0
        windspeed_value = f"{windspeed}m/s"
        
        # Create windspeed graph with properly aligned x and y values
        windspeed_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataWindspeed']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataWindspeed']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataWindspeed'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                windspeed_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                windspeed_fig.update_layout(
                    title="Windspeed Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="Windspeed (m/s)", range=[0, 70]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=300,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                windspeed_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#4B86FF', width=3),
                    showlegend=False
                ))
                windspeed_fig.update_layout(
                    title="Windspeed Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Windspeed (m/s)", range=[0, 70]),
                    height=300,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating windspeed graph: {e}")
            # Create a basic empty chart if there's an error
            windspeed_fig = go.Figure()
            windspeed_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        return windspeed_value, windspeed_fig
    
    except Exception as e:
        print(f"Error in update_th_in_dashboard: {e}")
        # Return default values if there's an error
        default_fig = go.Figure(layout=dict(
            title="Data Unavailable",
            annotations=[dict(
                text="Error loading data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )]
        ))
        return "N/A", default_fig
    
# Separate callback for rainfall layout - Completely revised version
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'rainfall-display'}, 'children', allow_duplicate=True),
     Output('rainfall-graph', 'figure')],
    [Input('interval_rainfall', 'n_intervals')],
    prevent_initial_call=True
)
def update_rainfall_dashboard(n):
    try:
        # Default values
        rainfall_value = "N/A"
        
        # Empty figures with proper layout
        empty_rainfall_fig = go.Figure(layout=dict(
            title="Rainfall Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Rainfall (mm)", range=[0, 100]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=300,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        # Check if we have data
        if not data['kodeDataRainfall'] or not data['waktu']:
            return rainfall_value, empty_rainfall_fig
        
        # Get the latest values
        rainfall = data['kodeDataRainfall'][-1] if data['kodeDataRainfall'] else 0
        rainfall_value = f"{rainfall}mm"
        
        # Create rainfall graph with properly aligned x and y values
        rainfall_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataRainfall']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataRainfall']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataRainfall'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                rainfall_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                rainfall_fig.update_layout(
                    title="Rainfall Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="Rainfall (mm)", range=[0, 100]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=300,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                rainfall_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#4B86FF', width=3),
                    showlegend=False
                ))
                rainfall_fig.update_layout(
                    title="Rainfall Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Rainfall (mm)", range=[0, 100]),
                    height=300,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating rainfall graph: {e}")
            # Create a basic empty chart if there's an error
            rainfall_fig = go.Figure()
            rainfall_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        return rainfall_value, rainfall_fig
    
    except Exception as e:
        print(f"Error in update_th_in_dashboard: {e}")
        # Return default values if there's an error
        default_fig = go.Figure(layout=dict(
            title="Data Unavailable",
            annotations=[dict(
                text="Error loading data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )]
        ))
        return "N/A", default_fig
    
# Separate callback for co2 layout - Completely revised version
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'co2-display'}, 'children', allow_duplicate=True),
     Output('co2-graph', 'figure')],
    [Input('interval_co2', 'n_intervals')],
    prevent_initial_call=True
)
def update_co2_dashboard(n):
    try:
        # Default values
        co2_value = "N/A"
        
        # Empty figures with proper layout
        co2_fig = go.Figure(layout=dict(
            title="CO2 Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="CO2 (PPM)", range=[400, 1000]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=300,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        # Check if we have data
        if not data['kodeDataCo2'] or not data['waktu']:
            return co2_value, co2_fig
        
        # Get the latest values
        co2 = data['kodeDataCo2'][-1] if data['kodeDataCo2'] else 0
        co2_value = f"{co2}PPM"
        

        # Create co2 graph with properly aligned x and y values
        co2_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataCo2']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataCo2']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataCo2'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                co2_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                co2_fig.update_layout(
                    title="CO2 Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="CO2 (PPM)", range=[0, 1000]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=300,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                co2_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#4B86FF', width=3),
                    showlegend=False
                ))
                co2_fig.update_layout(
                    title="CO2 Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="CO2 (PPM)", range=[0, 1000]),
                    height=300,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating co2 graph: {e}")
            # Create a basic empty chart if there's an error
            co2_fig = go.Figure()
            co2_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        return co2_value, co2_fig
    
    except Exception as e:
        print(f"Error in update_th_in_dashboard: {e}")
        # Return default values if there's an error
        default_fig = go.Figure(layout=dict(
            title="Data Unavailable",
            annotations=[dict(
                text="Error loading data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )]
        ))
        return "N/A", default_fig
    
# Separate callback for PAR layout - Completely revised version
@app_dash.callback(
    [Output({'type': 'sensor-value', 'id': 'par-display'}, 'children', allow_duplicate=True),
     Output('par-graph', 'figure')],
    [Input('interval_par', 'n_intervals')],
    prevent_initial_call=True
)
def update_par_dashboard(n):
    try:
        # Default values
        par_value = "N/A"
        
        # Empty figures with proper layout
        par_fig = go.Figure(layout=dict(
            title="PAR Trend",
            xaxis=dict(title="Time"),
            yaxis=dict(title="PAR (μmol/m²/s)", range=[0, 400]),
            margin=dict(l=40, r=20, t=40, b=30),
            height=300,
            plot_bgcolor='rgba(240, 240, 240, 0.9)'
        ))
        
        # Check if we have data
        if not data['kodeDataPar'] or not data['waktu']:
            return par_value, par_fig
        
        # Get the latest values
        par = data['kodeDataPar'][-1] if data['kodeDataPar'] else 0
        par_value = f"{par}μmol/m²/s"
        
        # Create par graph with properly aligned x and y values
        par_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['kodeDataPar']) > 3:
                # We'll use only 3 data points for simplicity
                num_points = 3
                
                # Select evenly spaced indices from the data
                indices = np.linspace(0, min(len(data['waktu']), len(data['kodeDataPar']))-1, num_points, dtype=int)
                
                # Get the selected timestamps and temperature values
                selected_timestamps = [data['waktu'][i] for i in indices]
                selected_values = [data['kodeDataPar'][i] for i in indices]
                
                # Create x values (0, 1, 2) for plotting
                x_plot = list(range(num_points))
                
                # Add the simplified line
                par_fig.add_trace(go.Scatter(
                    x=x_plot,  # Just use 0, 1, 2 for x values
                    y=selected_values,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Set up the axis with only 3 ticks
                par_fig.update_layout(
                    title="PAR Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=x_plot,  # [0, 1, 2]
                        ticktext=selected_timestamps,
                        tickangle=0
                    ),
                    yaxis=dict(title="PAR (μmol/m²/s)", range=[0, 400]),
                    margin=dict(l=40, r=20, t=40, b=30),
                    height=300,
                    plot_bgcolor='rgba(250, 250, 250, 0.9)',
                    showlegend=False
                )
                
            else:
                # Fallback for insufficient data
                par_fig.add_trace(go.Scatter(
                    x=[0, 1],
                    y=[0, 0],
                    mode='lines',
                    line=dict(color='#4B86FF', width=3),
                    showlegend=False
                ))
                par_fig.update_layout(
                    title="PAR Trend - Insufficient Data",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="PAR (μmol/m²/s)", range=[0, 400]),
                    height=300,
                    showlegend=False
                )
                
        except Exception as e:
            print(f"Error creating par graph: {e}")
            # Create a basic empty chart if there's an error
            par_fig = go.Figure()
            par_fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        return par_value, par_fig
    
    except Exception as e:
        print(f"Error in update_th_in_dashboard: {e}")
        # Return default values if there's an error
        default_fig = go.Figure(layout=dict(
            title="Data Unavailable",
            annotations=[dict(
                text="Error loading data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )]
        ))
        return "N/A", default_fig

# Add this function to help debug what's happening with your data
# and the table th_in
@app_dash.callback(
    Output('historical-table-th-in', 'data'),
    [Input('interval_thin', 'n_intervals')]
)
def update_historical_table(n):
    try:            
        # Create table data from the last 4 entries
        sample_size = min(2, len(data['waktu']))
        table_data = []
        
        for i in range(sample_size):
            idx = -(i+1)  # Index from the end of the list
            table_data.append({
                "time": data['waktu'][idx] if idx < len(data['waktu']) else "",
                "temperature_in_historical": f"{data['kodeDataSuhuIn'][idx]:.1f}%" if idx < len(data['kodeDataSuhuIn']) else "",
                "humidity_in_historical": f"{data['kodeDataKelembabanIn'][idx]:.1f}%" if idx < len(data['kodeDataKelembabanIn']) else ""
            })
            
        return table_data
    except Exception as e:
        print(f"Error in update_historical_table: {e}")
        return [{}]
    
# Callbacks to logout
@app_dash.callback(
    Output("logout-redirect", "href"),
    Input("logout-button", "n_clicks")
)
def logout_redirect(n_clicks):
    if n_clicks:
        return "/logout"  # Redirects to Flask route
    return None

# Callbacks to login
@app_dash.callback(
    Output("login-redirect", "href"),
    Input("login-button", "n_clicks")
)
def login_redirect(n_clicks):
    if n_clicks:
        return "/login"  # Redirects to Flask route
    return None

# Callback for GPS map
@app_dash.callback(
    [Output('gps-map', 'figure'),
     Output('current-location-text', 'children'),
     Output('current-coordinates', 'children')],
    [Input('interval_gps', 'n_intervals')]
)
def update_gps_data(n_intervals):
    """Update GPS map and location information using MQTT data"""
    # Add eFarming Corpora Community to LOCATIONS
    efarming_location = {"name": "eFarming Corpora Community", "lat": -6.880044, "lon": 107.6772643}
    
    # Create a local copy of locations including eFarming
    locations = LOCATIONS + [efarming_location]
    
    # Check if we have GPS data from MQTT
    if data["kodeDataLat"] and data["kodeDataLon"]:
        # Use the latest GPS coordinates from the MQTT data
        current_lat = data["kodeDataLat"][-1]
        current_lon = data["kodeDataLon"][-1]
        
        # Find closest known location
        min_distance = float('inf')
        location_name = "Unknown Location"
        for loc in locations:
            dist = ((loc["lat"] - current_lat)**2 + (loc["lon"] - current_lon)**2)**0.5
            if dist < min_distance:
                min_distance = dist
                location_name = f"Near {loc['name']}"
    else:
        # Fallback if no MQTT data is available
        current_lat = efarming_location["lat"]
        current_lon = efarming_location["lon"]
        location_name = "eFarming Corpora Community"
    
    # Create the map figure
    fig = go.Figure()
    
    # Add main device marker
    fig.add_trace(go.Scattermapbox(
        lat=[current_lat],
        lon=[current_lon],
        mode='markers',
        marker=dict(
            size=15,
            color='red',
        ),
        text=["Current Device Location"],
        name="Device"
    ))
    
    # Add known locations as reference points
    fig.add_trace(go.Scattermapbox(
        lat=[loc["lat"] for loc in locations],
        lon=[loc["lon"] for loc in locations],
        mode='markers',
        marker=dict(
            size=10,
            color='blue',
        ),
        text=[loc["name"] for loc in locations],
        name="Reference Points"
    ))
    
    # Add path history (last few points)
    # history_length = min(10, len(data["kodeDataLat"]))
    # if history_length > 1:
    #     # Get the last few GPS points from the MQTT data
    #     path_lats = data["kodeDataLat"][-history_length:]
    #     path_lons = data["kodeDataLon"][-history_length:]
        
    #     fig.add_trace(go.Scattermapbox(
    #         lat=path_lats,
    #         lon=path_lons,
    #         mode='lines',
    #         line=dict(width=2, color='orange'),
    #         name="Device Path"
    #     ))
    
    # Configure the map layout
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=current_lat, lon=current_lon),  # Center on current coordinates
            zoom=15,  # Default zoom level (slightly zoomed in)
            uirevision=f"{current_lat}_{current_lon}"  # Preserve zoom level while centered on current point
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    # Format coordinates as a string with 6 decimal places
    coordinates_text = f"{current_lat:.6f}, {current_lon:.6f}"
    
    return fig, location_name, coordinates_text

# Run server
if __name__ == '__main__':
    server.run(host='0.0.0.0', port=5000)
