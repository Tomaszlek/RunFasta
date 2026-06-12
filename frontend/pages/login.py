from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash
import requests

API = "https://127.0.0.1:8000"

# Layout strony logowania.
# Przyciski nawigacyjne (nav-to-register, nav-to-login) NIE są tu definiowane —
# żyją w app.layout jako zawsze obecne, żeby callbacki ich zawsze znajdowały.
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Logowanie", className="text-center mb-4"),
            dbc.Input(id='login-user', placeholder='Użytkownik', className="mb-2"),
            dbc.Input(id='login-pass', type='password', placeholder='Hasło', className="mb-2"),
            dbc.Button("Zaloguj", id='login-btn', color="primary", className="w-100 mb-2"),
            dbc.Button("Nie masz konta? Zarejestruj się",
                       id='nav-to-register-visible', color="link", className="w-100 text-muted"),
            html.Div(id='login-alert', className="mt-2")
        ], width=4)
    ], justify="center", style={"marginTop": "15%"})
])


def register_callbacks(app):
    @app.callback(
        [Output('session-auth', 'data', allow_duplicate=True),
         Output('login-alert', 'children')],
        Input('login-btn', 'n_clicks'),
        [State('login-user', 'value'), State('login-pass', 'value')],
        prevent_initial_call=True
    )
    def login(n, user, password):
        if not user or not password:
            return dash.no_update, dbc.Alert("Podaj login i hasło!", color="warning")
        try:
            res = requests.get(f"{API}/me", auth=(user, password), verify=False)
            if res.status_code == 200:
                return {'user': user, 'pass': password, 'role': res.json()['role']}, ""
            return dash.no_update, dbc.Alert("Błędne dane logowania!", color="danger")
        except Exception:
            return dash.no_update, dbc.Alert("Brak połączenia z serwerem!", color="warning")

    # Przycisk "Zarejestruj się" widoczny na stronie logowania
    # triggeruje ukryty nav-to-register w app.layout
    @app.callback(
        Output('nav-to-register', 'n_clicks'),
        Input('nav-to-register-visible', 'n_clicks'),
        prevent_initial_call=True
    )
    def proxy_to_register(n):
        if n:
            return n
        return dash.no_update