# pages/main_dashboard.py

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

main_dashboard_layout = html.Div([
    # NAVBAR
    html.Div([
        html.Div("MICROCLIMATE SYSTEM DASHBOARD", className="navbar-title"),
        dcc.Link(html.Img(src="/static/icon/gps.svg", className="gps-icon me-2"), href="/dash/gps"),
        dcc.Link(html.Img(src="/static/icon/notification.svg", className="notification-icon"), href="/dash/alarm"),
    ], className="d-flex justify-content-between align-items-center p-3 border-bottom navbar-full"),

    # TAMPILAN PARAMETER SENSOR GRID
    html.Div([
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.Div([
                        html.Img(src="/static/icon/temperature.svg", className="param-icon me-2"),
                        html.Span("TEMPERATURE IN", className="param-title me-2"),
                        html.Span(id={'type': 'sensor-value', 'id': 'suhu-display-indoor'}, className="param-value")
                    ], className="d-flex align-items-center mb-2"),
                    html.Div([
                        html.Img(src="/static/icon/humidity.svg", className="param-icon me-2"),
                        html.Span("HUMIDITY IN", className="param-title me-2"),
                        html.Span(id={'type': 'sensor-value', 'id': 'kelembaban-display-indoor'}, className="param-value")
                    ], className="d-flex align-items-center")
                ])
            ], className="param-card"), width=4),

            dbc.Col(html.Div([
                html.Div([
                    html.Img(src="/static/icon/sun.svg", className="param-icon me-2"),
                    html.Span("PAR", className="param-title me-2"),
                    html.Span(id={'type': 'sensor-value', 'id': 'par-display'}, className="param-value")
                ], className="d-flex align-items-center")
            ], className="param-card"), width=4),

            dbc.Col(html.Div([
                html.Div([
                    html.Img(src="/static/icon/co.svg", className="param-icon me-2"),
                    html.Span("CO2", className="param-title me-2"),
                    html.Span(id={'type': 'sensor-value', 'id': 'co2-display'}, className="param-value")
                ], className="d-flex align-items-center")
            ], className="param-card"), width=4),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.Div([
                        html.Img(src="/static/icon/temperature.svg", className="param-icon me-2"),
                        html.Span("TEMPERATURE OUT", className="param-title me-2"),
                        html.Span(id={'type': 'sensor-value', 'id': 'suhu-display-outdoor'}, className="param-value")
                    ], className="d-flex align-items-center mb-2"),
                    html.Div([
                        html.Img(src="/static/icon/humidity.svg", className="param-icon me-2"),
                        html.Span("HUMIDITY OUT", className="param-title me-2"),
                        html.Span(id={'type': 'sensor-value', 'id': 'kelembaban-display-outdoor'}, className="param-value")
                    ], className="d-flex align-items-center")
                ])
            ], className="param-card"), width=4),

            dbc.Col(html.Div([
                html.Div([
                    html.Img(src="/static/icon/windspeed.svg", className="param-icon me-2"),
                    html.Span("WINDSPEED", className="param-title me-2"),
                    html.Span(id={'type': 'sensor-value', 'id': 'windspeed-display'}, className="param-value")
                ], className="d-flex align-items-center")
            ], className="param-card"), width=4),

            dbc.Col(html.Div([
                html.Div([
                    html.Img(src="/static/icon/rainfall.svg", className="param-icon me-2"),
                    html.Span("RAINFALL", className="param-title me-2"),
                    html.Span(id={'type': 'sensor-value', 'id': 'rainfall-display'}, className="param-value")
                ], className="d-flex align-items-center")
            ], className="param-card"), width=4),
        ])
    ], className="container"),

    # TAMPILAN BOTTOM GRID
    html.Div([
        dbc.Row([
            dbc.Col(html.Img(src="/static/img/pictogram_mcs_2.png", className="greenhouse-img"), width=6),
            dbc.Col([
                # Table Section
                html.Div([
                    html.H4("Real Time Table", className="text-center mb-2"),
                    dash_table.DataTable(
                        columns=[
                            {"name": i, "id": i} for i in [
                                "Temp (°C)", "Humidity (%)", "PAR (2-s-1)", "CO2 (PPM)", "Windspeed (m/s)", "Rainfall (mm)"
                            ]
                        ],
                        data=[],
                        style_table={'overflowX': 'auto'},
                        style_cell={"textAlign": "center"}
                    )
                ], className="data-table mb-3"),

                # Button Section
                html.Div([
                    # html.Button("SETTING", className="btn btn-secondary m-1"),
                    dcc.Link("T&H INDOOR", href="/dash/th-in", className="btn btn-secondary m-1"),
                    dcc.Link("PAR", href="/dash/par", className="btn btn-secondary m-1"),
                    dcc.Link("CO2", href="/dash/co2", className="btn btn-secondary m-1"),
                    dcc.Link("T&H OUTDOOR", href="/dash/th-out", className="btn btn-secondary m-1"),
                    dcc.Link("WINDSPEED", href="/dash/windspeed", className="btn btn-secondary m-1"),
                    dcc.Link("RAINFALL", href="/dash/rainfall", className="btn btn-secondary m-1"),
                    html.Button("LOGIN", id="login-button", className="btn btn-dark m-1"),
                    dcc.Location(id="login-redirect", refresh=True)  # Handles redirection
                ], className="d-flex flex-wrap justify-content-end")
            ], width=6)
        ], className="g-2")
    ], className="container mb-5"),

    dcc.Interval(id='interval_mcs', interval=1200, n_intervals=0)
])

# routing path untuk halaman utama
main_dashboard_path = "/dash/"