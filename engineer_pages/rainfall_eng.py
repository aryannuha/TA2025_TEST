from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

engineer_rainfall_layout = html.Div([
    # NAVBAR
    html.Div([
        html.Div("RAINFALL DASHBOARD", className="navbar-title"),
        dcc.Link(html.Img(src="/static/icon/gps.svg", className="gps-icon me-2"), href="/dash/engineer/gps"),
        dcc.Link(html.Img(src="/static/icon/notification.svg", className="notification-icon"), href="/dash/engineer/alarm"),
    ], className="d-flex justify-content-between align-items-center p-3 border-bottom navbar-full mb-1"),
    
    # MAIN CONTENT
    html.Div([
        dbc.Row([
            # LEFT SIDE - Parameter Cards and Greenhouse Image
            dbc.Col([
                # Rainfall in a row
                dbc.Row([
                    # Rainfall Card
                    dbc.Col(
                        html.Div([
                            html.Img(src="/static/icon/rainfall.svg", className="param-icon me-2"),
                            html.H5("RAINFALL", className="mb-2"),
                            html.H3(id={'type': 'sensor-value', 'id': 'rainfall-display'}, className="fw-bold")
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
                                id='rainfall-graph',
                                config={"displayModeBar": False},
                                style={'height': '300px'}
                            )
                        ]), 
                    ], className="mb-3 p-2 border rounded bg-light"),
                
                # Historical Data Table
                html.Div([
                    html.H5("HISTORICAL TABLE", className="text-center mb-2"),
                    dash_table.DataTable(
                        id='historical-table-rainfall',
                        columns=[
                            {"name": "Time (h)", "id": "time"},
                            {"name": "Rainfall (mm)", "id": "rainfall-historical"},
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
                    dcc.Link("MCS", href="/dash/engineer/", className="btn btn-secondary m-1"),
                    dcc.Link("PAR", href="/dash/engineer/par", className="btn btn-secondary m-1"),
                    dcc.Link("CO2", href="/dash/engineer/co2", className="btn btn-secondary m-1"),
                    dcc.Link("T&H INDOOR", href="/dash/engineer/th-in", className="btn btn-secondary m-1"),
                    dcc.Link("T&H OUTDOOR", href="/dash/engineer/th-out", className="btn btn-secondary m-1"),
                    dcc.Link("WINDSPEED", href="/dash/engineer/windspeed", className="btn btn-secondary m-1"),
                    html.Button("LOGOUT", id="logout-button", className="btn btn-dark m-1"),
                    dcc.Location(id="logout-redirect", refresh=True)  # Handles redirection
                ], className="d-flex justify-content-end")
            ], width=6, className="ps-3")
        ])
    ], className="container"),
    
    # Keep the interval component for data updates
    dcc.Interval(id='interval_rainfall', interval=1200, n_intervals=0)
], className="dashboard-container")
