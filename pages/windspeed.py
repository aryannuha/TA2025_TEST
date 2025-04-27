from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

windspeed_layout = html.Div([
    # NAVBAR
    html.Div([
        html.Div("WINDSPEED DASHBOARD", className="navbar-title"),
        dcc.Link(html.Img(src="/static/icon/gps.svg", className="gps-icon me-2"), href="/dash/gps"),
        dcc.Link(html.Img(src="/static/icon/notification.svg", className="notification-icon"), href="/dash/alarm"),
    ], className="d-flex justify-content-between align-items-center p-3 border-bottom navbar-full mb-1"),
    
    # MAIN CONTENT
    html.Div([
        dbc.Row([
            # LEFT SIDE - Parameter Cards and Greenhouse Image
            dbc.Col([
                # Windspeed in a row
                dbc.Row([
                    # Windspeed Card
                    dbc.Col(
                        html.Div([
                            html.Img(src="/static/icon/windspeed.svg", className="param-icon me-2"),
                            html.H5("WINDSPEED", className="mb-2"),
                            html.H3(id={'type': 'sensor-value', 'id': 'windspeed-display'}, className="fw-bold")
                        ], className="parameter-card p-3 h-100 border rounded"),
                    width=12),
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
                        
                        # Windspeed Graph - Using a simple div wrapper
                        html.Div([
                            dcc.Graph(
                                id='windspeed-graph',
                                config={"displayModeBar": False},
                                style={'height': '300px'}
                            )
                        ]), 
                    ], className="mb-3 p-2 border rounded bg-light"),
                
                # Historical Data Table
                html.Div([
                    html.H5("HISTORICAL TABLE", className="text-center mb-2"),
                    dash_table.DataTable(
                        id='historical-table-windspeed',
                        columns=[
                            {"name": "Time (h)", "id": "time"},
                            {"name": "Windspeed (m/s)", "id": "windspeed-historical"},
                        ],
                        data=[
                            # Empty rows for demonstration
                            {} for _ in range(2)
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
                    # html.Button("SETTING", className="btn btn-secondary m-1"),
                    dcc.Link("MCS", href="/dash/", className="btn btn-secondary m-1"),
                    dcc.Link("PAR", href="/dash/par", className="btn btn-secondary m-1"),
                    dcc.Link("CO2", href="/dash/co2", className="btn btn-secondary m-1"),
                    dcc.Link("T&H INDOOR", href="/dash/th-in", className="btn btn-secondary m-1"),
                    dcc.Link("T&H OUTDOOR", href="/dash/th-out", className="btn btn-secondary m-1"),
                    dcc.Link("RAINFALL", href="/dash/rainfall", className="btn btn-secondary m-1"),
                    html.Button("LOGIN", id="login-button", className="btn btn-dark m-1"),
                    dcc.Location(id="login-redirect", refresh=True)  # Handles redirection
                ], className="d-flex justify-content-end")
            ], width=6, className="ps-3")
        ])
    ], className="container"),
    
    # Keep the interval component for data updates
    dcc.Interval(id='interval_windspeed', interval=1200, n_intervals=0)
], className="dashboard-container")