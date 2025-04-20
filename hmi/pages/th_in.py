from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

th_in_layout = html.Div([
    # NAVBAR
    html.Div([
        html.Div("T&H DASHBOARD", className="navbar-title"),
        html.Img(src="/static/icon/notification.svg", className="notification-icon"),
    ], className="d-flex justify-content-between align-items-center p-3 border-bottom navbar-full mb-1"),
    
    # MAIN CONTENT
    html.Div([
        dbc.Row([
            # LEFT SIDE - Parameter Cards and Greenhouse Image
            dbc.Col([
                # Temperature and Humidity Cards in a row
                dbc.Row([
                    # Temperature Card
                    dbc.Col(
                        html.Div([
                            html.Img(src="/static/icon/temperature.svg", className="param-icon me-2"),
                            html.H5("TEMPERATURE", className="mb-2"),
                            html.H3(id="suhu-display-indoor", className="fw-bold")
                        ], className="parameter-card p-3 h-100 border rounded"),
                    width=6),
                    
                    # Humidity Card
                    dbc.Col(
                        html.Div([
                            html.Img(src="/static/icon/humidity.svg", className="param-icon me-2"),
                            html.H5("HUMIDITY", className="mb-2"),
                            html.H3(id="kelembaban-display-indoor", className="fw-bold")
                        ], className="parameter-card p-3 h-100 border rounded"),
                    width=6),
                ], className="mb-3"),
                
                # Greenhouse Image
                html.Div([
                    html.Img(src="/static/img/gh.jpg", className="img-fluid w-100 border border-primary p-1", 
                            style={"height": "300px", "object-fit": "cover"})
                ], className="greenhouse-container")
            ], width=6, className="pe-3"),
            
           # RIGHT SIDE - Graphs and Table
                dbc.Col([
                    # Real-time Trend Graphs with clear IDs and sufficient height
                    html.Div([
                        html.H5("REAL-TIME TREND", className="text-center mb-2"),
                        
                        # Temperature Graph with explicit height
                        html.Div([
                            dcc.Graph(
                                id='temp-graph',
                                style={'height': '150px'},  # Explicit height
                            )
                        ]), 
                        
                        # Humidity Graph with explicit height
                        html.Div([
                            dcc.Graph(
                                id='humidity-graph',
                                style={'height': '150px'},  # Explicit height
                            )
                        ]), 
                    ], className="mb-3 p-2 border rounded bg-light"),
                
                # Historical Data Table
                html.Div([
                    html.H5("HISTORICAL TABLE", className="text-center mb-2"),
                    dash_table.DataTable(
                        id='historical-table',
                        columns=[
                            {"name": "Time (h)", "id": "time"},
                            {"name": "Humidity (%)", "id": "humidity"},
                            {"name": "PAR (2-s-1)", "id": "par"},
                            {"name": "CO2 (PPM)", "id": "co2"},
                            {"name": "Volt (V)", "id": "volt"},
                            {"name": "Current (A)", "id": "current"},
                            {"name": "Energy (kWh)", "id": "energy"}
                        ],
                        data=[
                            # Empty rows for demonstration
                            {} for _ in range(4)
                        ],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'center', 'padding': '5px'},
                        style_header={
                            'backgroundColor': '#f8f9fa',
                            'fontWeight': 'bold'
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': '#f8f9fa'
                            }
                        ]
                    )
                ], className="mb-3 p-2 border rounded bg-light"),
                
                # Buttons
                html.Div([
                    html.Button("SETTING", className="btn btn-secondary m-1"),
                    dcc.Link("MAIN MENU", href="/dash/", className="btn btn-secondary m-1"),
                    dcc.Link("T&H INDOOR", href="/dash/th-in", className="btn btn-secondary m-1"),
                    dcc.Link("PAR", href="/dash/par", className="btn btn-secondary m-1"),
                    dcc.Link("CO2", href="/dash/co2", className="btn btn-secondary m-1"),
                    dcc.Link("T&H OUTDOOR", href="/dash/th-out", className="btn btn-secondary m-1"),
                    dcc.Link("WINDSPEED", href="/dash/windspeed", className="btn btn-secondary m-1"),
                    dcc.Link("RAINFALL", href="/dash/rainfall", className="btn btn-secondary m-1"),
                    html.Button("LOGOUT", id="logout-button", className="btn btn-dark m-1"),
                    dcc.Location(id="logout-redirect", refresh=True)  # Handles redirection
                ], className="d-flex justify-content-end")
            ], width=6, className="ps-3")
        ])
    ], className="container"),
    
    # Keep the interval component for data updates
    dcc.Interval(id='interval', interval=1100, n_intervals=0)
], className="dashboard-container")