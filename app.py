# Author: Ammar Aryan Nuha
# Deklarasi library yang digunakan
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import dash
import dash_bootstrap_components as dbc
import secrets
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import threading
import ssl
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

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)

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
# end of flask route

# Integrate Dash app
app_dash = dash.Dash(__name__, server=server, url_base_pathname='/dash/', external_stylesheets=[dbc.themes.BOOTSTRAP], title='MCS Dashboard', suppress_callback_exceptions=True)
 
@app_dash.server.before_request
def restrict_dash_pages():
    if not current_user.is_authenticated and request.path.startswith('/dash'):
        return redirect(url_for('login'))

# data storage
data = {
    'waktu': [],      # Time values
    'suhu': [],       # Temperature values 
    'kelembaban': [], # Humidity values
    'suhu_out': [],   # Outdoor temperature values
    'kelembaban_out': [], # Outdoor humidity values
    'co2': [],        # CO2 values
    'windspeed': [],  # Wind speed values
    'rainfall': [],    # Rainfall values
    'par': []    # Rainfall values
}

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
TOPIC_SUHU = "esp32/suhu"
TOPIC_KELEMBABAN = "esp32/kelembaban"
TOPIC_SUHU_OUT = "esp32/suhu_out"
TOPIC_KELEMBABAN_OUT = "esp32/kelembaban_out"
TOPIC_CO2 = "esp32/co2"
TOPIC_WINDSPEED = "esp32/windspeed"
TOPIC_RAINFALL = "esp32/rainfall"
TOPIC_PAR = "esp32/par"

# MQTT Callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to HiveMQ Broker")
        client.subscribe([(TOPIC_SUHU, 0), (TOPIC_KELEMBABAN, 0),
                          (TOPIC_SUHU_OUT, 0), (TOPIC_KELEMBABAN_OUT, 0),
                          (TOPIC_CO2, 0), (TOPIC_WINDSPEED, 0), 
                          (TOPIC_RAINFALL, 0), (TOPIC_PAR, 0)])  # Subscribe ke topik suhu & kelembaban
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    global data
    try:
        topic = msg.topic.split('/')[-1]  # Get the last part of the topic (e.g., 'suhu' from 'esp32/suhu')
        payload = float(msg.payload.decode())
        
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Initialize lists if they don't exist
        if topic in ['suhu', 'kelembaban', 'suhu_out', 'kelembaban_out', 'co2', 'windspeed', 'rainfall', 'par']:
            if len(data[topic]) >= 20:  # Keep only last 20 points
                data[topic] = data[topic][1:]
            data[topic].append(payload)
            
            # Keep waktu list in sync with the latest data addition
            # This ensures all lists have the same length
            if topic == 'suhu':  # Only update waktu when temperature data comes in
                if len(data['waktu']) >= 20:
                    data['waktu'] = data['waktu'][1:]
                data['waktu'].append(current_time)
                
            # Debug output
            # print(f"Received {topic} data: {payload}, time: {current_time}")
            # print(f"Data lengths: waktu={len(data['waktu'])}, {topic}={len(data[topic])}")

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
def render_page_content(pathname):
    return pages.get(pathname, html.Div("404 - Page not found"))

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
        suhu = data['suhu'][-1] if data['suhu'] else 0
        kelembaban = data['kelembaban'][-1] if data['kelembaban'] else 0
        suhu_out = data['suhu_out'][-1] if data['suhu_out'] else 0
        kelembaban_out = data['kelembaban_out'][-1] if data['kelembaban_out'] else 0
        co2 = data['co2'][-1] if data['co2'] else 0
        windspeed = data['windspeed'][-1] if data['windspeed'] else 0
        rainfall = data['rainfall'][-1] if data['rainfall'] else 0
        par = data['par'][-1] if data['par'] else 0

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

        # print(f"DEBUG: Data lengths - waktu: {len(data['waktu'] if 'waktu' in data else [])}, " 
        # f"suhu: {len(data['suhu'] if 'suhu' in data else [])}, "
        # f"kelembaban: {len(data['kelembaban'] if 'kelembaban' in data else [])}")
        
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
        if not data['suhu'] or not data['kelembaban'] or not data['waktu']:
            return suhu_value, kelembaban_value, empty_temp_fig, empty_humid_fig
        
        # Get the latest values
        suhu = data['suhu'][-1] if data['suhu'] else 0
        kelembaban = data['kelembaban'][-1] if data['kelembaban'] else 0
        suhu_value = f"{suhu}°C"
        kelembaban_value = f"{kelembaban}%"
        
        # Create temperature graph with properly aligned x and y values
        temp_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['suhu']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['suhu']))
                timestamps = data['waktu'][:min_length]
                suhu_values = data['suhu'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, suhu_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                temp_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#FF4B4B', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                temp_fig.update_layout(
                    title="Temperature Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="Temperature (°C)", range=[0, 40]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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
            if len(data['waktu']) > 3 and len(data['kelembaban']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['kelembaban']))
                timestamps = data['waktu'][:min_length]
                kelembaban_values = data['kelembaban'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, kelembaban_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                humid_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                humid_fig.update_layout(
                    title="Humidity Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="Humidity (%)", range=[40, 100]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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

        # Create temperature graph
        # temp_fig = go.Figure()
        # temp_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['suhu'],
        #     mode='lines+markers',
        #     name='Temperature',
        #     line=dict(color='#FF4B4B', width=2),
        #     marker=dict(size=6)
        # ))
        # temp_fig.update_layout(
        #     title="Temperature Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="Temperature (°C)", range=[0, 40]),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=150,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
        
        # Create humidity graph
        # humid_fig = go.Figure()
        # humid_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['kelembaban'],
        #     mode='lines+markers',
        #     name='Humidity',
        #     line=dict(color='blue', width=2),
        #     marker=dict(size=6)
        # ))
        # humid_fig.update_layout(
        #     title="Humidity Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="Humidity (%)", range=[40, 100]),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=150,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
        
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
def update_th_in_dashboard(n):
    try:

        # print(f"DEBUG: Data lengths - waktu: {len(data['waktu'] if 'waktu' in data else [])}, " 
        # f"suhu: {len(data['suhu_out'] if 'suhu_out' in data else [])}, "
        # f"kelembaban: {len(data['kelembaban_out'] if 'kelembaban_out' in data else [])}")
        
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
        if not data['suhu_out'] or not data['kelembaban_out'] or not data['waktu']:
            return suhu_value, kelembaban_value, empty_temp_fig, empty_humid_fig
        
        # Get the latest values
        suhu = data['suhu_out'][-1] if data['suhu_out'] else 0
        kelembaban = data['kelembaban_out'][-1] if data['kelembaban_out'] else 0
        suhu_value = f"{suhu}°C"
        kelembaban_value = f"{kelembaban}%"

        # Create temperature graph with properly aligned x and y values
        temp_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['suhu_out']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['suhu_out']))
                timestamps = data['waktu'][:min_length]
                suhu_values = data['suhu_out'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, suhu_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                temp_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#FF4B4B', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                temp_fig.update_layout(
                    title="Temperature Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="Temperature (°C)", range=[0, 40]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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
            if len(data['waktu']) > 3 and len(data['kelembaban_out']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['kelembaban_out']))
                timestamps = data['waktu'][:min_length]
                kelembaban_values = data['kelembaban_out'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, kelembaban_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                humid_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                humid_fig.update_layout(
                    title="Humidity Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="Humidity (%)", range=[40, 100]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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
        
        # Create temperature graph
        # temp_fig = go.Figure()
        # temp_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['suhu_out'],
        #     mode='lines+markers',
        #     name='Temperature',
        #     line=dict(color='#FF4B4B', width=2),
        #     marker=dict(size=6)
        # ))
        # temp_fig.update_layout(
        #     title="Temperature Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="Temperature (°C)"),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=150,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
        
        # Create humidity graph
        # humid_fig = go.Figure()
        # humid_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['kelembaban_out'],
        #     mode='lines+markers',
        #     name='Humidity',
        #     line=dict(color='blue', width=2),
        #     marker=dict(size=6)
        # ))
        # humid_fig.update_layout(
        #     title="Humidity Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="Humidity (%)"),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=150,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
        
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
def update_th_in_dashboard(n):
    try:

        # print(f"DEBUG: Data lengths - waktu: {len(data['waktu'] if 'waktu' in data else [])}, " 
        # f"suhu: {len(data['suhu'] if 'suhu' in data else [])}, "
        # f"kelembaban: {len(data['kelembaban'] if 'kelembaban' in data else [])}")
        
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
        if not data['windspeed'] or not data['waktu']:
            return windspeed_value, empty_windspeed_fig
        
        # Get the latest values
        windspeed = data['windspeed'][-1] if data['windspeed'] else 0
        windspeed_value = f"{windspeed}m/s"
        
        # Create windspeed graph with properly aligned x and y values
        windspeed_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['windspeed']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['windspeed']))
                timestamps = data['waktu'][:min_length]
                windspeed_values = data['windspeed'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, windspeed_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                windspeed_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                windspeed_fig.update_layout(
                    title="Windspeed Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="Windspeed (m/s)", range=[0, 70]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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

        # Create Windspeed graph
        # windspeed_fig = go.Figure()
        # windspeed_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['windspeed'],
        #     mode='lines+markers',
        #     name='Windspeed',
        #     line=dict(color='#FF4B4B', width=2),
        #     marker=dict(size=6)
        # ))
        # windspeed_fig.update_layout(
        #     title="Windspeed Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="Windspeed (m/s)", range=[0, 70]),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=300,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
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
def update_th_in_dashboard(n):
    try:

        # print(f"DEBUG: Data lengths - waktu: {len(data['waktu'] if 'waktu' in data else [])}, " 
        # f"suhu: {len(data['suhu'] if 'suhu' in data else [])}, "
        # f"kelembaban: {len(data['kelembaban'] if 'kelembaban' in data else [])}")
        
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
        if not data['rainfall'] or not data['waktu']:
            return rainfall_value, empty_rainfall_fig
        
        # Get the latest values
        rainfall = data['rainfall'][-1] if data['rainfall'] else 0
        rainfall_value = f"{rainfall}mm"
        
        # Create rainfall graph with properly aligned x and y values
        rainfall_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['rainfall']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['rainfall']))
                timestamps = data['waktu'][:min_length]
                rainfall_values = data['rainfall'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, rainfall_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                rainfall_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                rainfall_fig.update_layout(
                    title="Rainfall Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="Rainfall (mm)", range=[0, 100]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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
        # Create rainfall graph
        # rainfall_fig = go.Figure()
        # rainfall_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['rainfall'],
        #     mode='lines+markers',
        #     name='Rainfall',
        #     line=dict(color='#FF4B4B', width=2),
        #     marker=dict(size=6)
        # ))
        # rainfall_fig.update_layout(
        #     title="Rainfall Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="Rainfall (mm)", range=[0, 100]),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=300,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
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
def update_th_in_dashboard(n):
    try:

        # print(f"DEBUG: Data lengths - waktu: {len(data['waktu'] if 'waktu' in data else [])}, " 
        # f"suhu: {len(data['suhu'] if 'suhu' in data else [])}, "
        # f"kelembaban: {len(data['kelembaban'] if 'kelembaban' in data else [])}")
        
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
        if not data['co2'] or not data['waktu']:
            return co2_value, co2_fig
        
        # Get the latest values
        co2 = data['co2'][-1] if data['co2'] else 0
        co2_value = f"{co2}PPM"
        

        # Create co2 graph with properly aligned x and y values
        co2_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['co2']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['co2']))
                timestamps = data['waktu'][:min_length]
                co2_values = data['co2'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, co2_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                co2_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                co2_fig.update_layout(
                    title="CO2 Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="CO2 (PPM)", range=[0, 1000]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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
        # Create rainfall graph
        # co2_fig = go.Figure()
        # co2_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['co2'],
        #     mode='lines+markers',
        #     name='CO2',
        #     line=dict(color='#FF4B4B', width=2),
        #     marker=dict(size=6)
        # ))
        # co2_fig.update_layout(
        #     title="CO2 Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="CO2 (mm)", range=[400, 1000]),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=300,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
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
def update_th_in_dashboard(n):
    try:

        # print(f"DEBUG: Data lengths - waktu: {len(data['waktu'] if 'waktu' in data else [])}, " 
        # f"suhu: {len(data['suhu'] if 'suhu' in data else [])}, "
        # f"kelembaban: {len(data['kelembaban'] if 'kelembaban' in data else [])}")
        
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
        if not data['par'] or not data['waktu']:
            return par_value, par_fig
        
        # Get the latest values
        par = data['par'][-1] if data['par'] else 0
        par_value = f"{par}μmol/m²/s"
        
        # Create par graph with properly aligned x and y values
        par_fig = go.Figure()

        try:
            # Ensure we have data to work with
            if len(data['waktu']) > 3 and len(data['par']) > 3:
                # Make sure x and y have the same length (this is crucial)
                min_length = min(len(data['waktu']), len(data['par']))
                timestamps = data['waktu'][:min_length]
                par_values = data['par'][:min_length]
                
                # Create evenly spaced x-indices
                x_indices = list(range(min_length))
                
                # Create interpolation points - keeping x as simple numeric indices
                x_new = np.linspace(0, min_length-1, num=300)
                
                # Create the smooth interpolation
                cs = interpolate.CubicSpline(x_indices, par_values, bc_type='natural')
                y_smooth = cs(x_new)
                
                # Add smooth curve with numeric x-axis
                par_fig.add_trace(go.Scatter(
                    x=x_new,  # Numeric x-axis
                    y=y_smooth,
                    mode='lines',
                    line=dict(color='#4B86FF', width=3, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(75, 134, 255, 0.2)',
                    showlegend=False
                ))
                
                # Configure fixed x-axis ticks with actual timestamps
                num_ticks = min(8, min_length)  # Show at most 8 ticks
                tick_indices = np.linspace(0, min_length-1, num_ticks, dtype=int)
                tick_labels = [timestamps[i] for i in tick_indices]
                
                par_fig.update_layout(
                    title="PAR Trend",
                    xaxis=dict(
                        title="Time",
                        tickmode='array',
                        tickvals=tick_indices,  # Use numeric values for tick positions
                        ticktext=tick_labels,   # Use actual timestamps as labels
                        tickangle=45
                    ),
                    yaxis=dict(title="PAR (μmol/m²/s)", range=[0, 400]),
                    margin=dict(l=40, r=20, t=40, b=60),  # Extra space at bottom for labels
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
                    yaxis=dict(title="PAR (μmol/m²/s)", range=[0, 100]),
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
        # Create Windspeed graph
        # par_fig = go.Figure()
        # par_fig.add_trace(go.Scatter(
        #     x=data['waktu'],
        #     y=data['par'],
        #     mode='lines+markers',
        #     name='Par',
        #     line=dict(color='#FF4B4B', width=2),
        #     marker=dict(size=6)
        # ))
        # par_fig.update_layout(
        #     title="PAR Trend",
        #     xaxis=dict(title="Time"),
        #     yaxis=dict(title="PAR (μmol/m²/s)", range=[0, 400]),
        #     margin=dict(l=40, r=20, t=40, b=30),
        #     height=300,
        #     plot_bgcolor='rgba(240, 240, 240, 0.9)'
        # )
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
        # Print debug info to console
        # print(f"Data lengths: waktu={len(data['waktu'])}, suhu={len(data['suhu'])}, kelembaban={len(data['kelembaban'])}")
        # if data['waktu']:
        #     print(f"Sample data: waktu={data['waktu'][-1]}, suhu={data['suhu'][-1]}, kelembaban={data['kelembaban'][-1]}")
        
        # if not data['waktu']:
        #     return [{}]
            
        # Create table data from the last 4 entries
        sample_size = min(4, len(data['waktu']))
        table_data = []
        
        for i in range(sample_size):
            idx = -(i+1)  # Index from the end of the list
            table_data.append({
                "time": data['waktu'][idx] if idx < len(data['waktu']) else "",
                "temperature_in_historical": f"{data['suhu'][idx]:.1f}%" if idx < len(data['suhu']) else "",
                "humidity_in_historical": f"{data['kelembaban'][idx]:.1f}%" if idx < len(data['kelembaban']) else ""
            })
            
        return table_data
    except Exception as e:
        print(f"Error in update_historical_table: {e}")
        return [{}]
    
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