from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

# GPS DASHBOARD LAYOUT
gps_layout = html.Div([
     # NAVBAR
    html.Div([
        html.Div("GPS DASHBOARD", className="navbar-title"),
        dcc.Link(html.Img(src="/static/icon/gps.svg", className="gps-icon me-2"), href="/dash/gps"),
        dcc.Link(html.Img(src="/static/icon/notification.svg", className="notification-icon"), href="/dash/alarm"),
    ], className="d-flex justify-content-between align-items-center p-3 border-bottom navbar-full"),
])