import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import requests
import pandas as pd
from datetime import date

API = "https://127.0.0.1:8000"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

app.layout = html.Div([
    dcc.Store(id='session-auth', storage_type='session'),
    dcc.Store(id='current-page', data='login'),
    dcc.Download(id="download-pdf"),
    dcc.Interval(id='auto-refresh', interval=3000, n_intervals=0),
    html.Div(id='page-content')
])

login_layout = dbc.Container([
    html.Div([
        html.Button("x", id='show-register-btn', style={'display': 'none'}),
        html.Button("x", id='show-login-btn', style={'display': 'none'}),
    ]),
    dbc.Row([
        dbc.Col([
            html.H2("Logowanie", className="text-center mb-4"),
            dbc.Input(id='login-user', placeholder='Użytkownik', className="mb-2"),
            dbc.Input(id='login-pass', type='password', placeholder='Hasło', className="mb-2"),
            dbc.Button("Zaloguj", id='login-btn', color="primary", className="w-100 mb-2"),
            dbc.Button("Nie masz konta? Zarejestruj się", id='show-register-btn-visible', color="secondary", className="w-100"),
            html.Div(id='login-alert', className="mt-2")
        ], width=4)
    ], justify="center", style={"marginTop": "15%"})
])


register_layout = dbc.Container([
    html.Div([
        html.Button("x", id='show-register-btn', style={'display': 'none'}),
        html.Button("x", id='show-login-btn', style={'display': 'none'}),
    ]),
    dbc.Row([
        dbc.Col([
            html.H2("Rejestracja", className="text-center mb-4"),
            dbc.Input(id='register-user', placeholder='Nazwa użytkownika', className="mb-2"),
            dbc.Input(id='register-pass', type='password', placeholder='Hasło', className="mb-2"),
            dcc.Dropdown(id='register-role', 
                        options=[
                            {'label': 'Trener', 'value': 'COACH'},
                            {'label': 'Biegacz', 'value': 'RUNNER'}
                        ],
                        placeholder="Wybierz rolę", className="mb-2"),
            dbc.Button("Zarejestruj się", id='register-btn', color="success", className="w-100 mb-2"),
            dbc.Button("Wróć do logowania", id='show-login-btn-visible', color="secondary", className="w-100"),
            html.Div(id='register-alert', className="mt-2")
        ], width=4)
    ], justify="center", style={"marginTop": "15%"})
])


def dashboard_layout(username, role):
    if role == "COACH":
        hidden = html.Div([
            dcc.Input(id='r-dist', style={'display': 'none'}),
            dcc.Input(id='r-time', style={'display': 'none'}),
            dcc.Input(id='r-note', style={'display': 'none'}),
            dcc.Button(id='r-save-btn', style={'display': 'none'}),
            html.Div(id='runner-total-dist', style={'display': 'none'}),
            html.Div(id='runner-count', style={'display': 'none'}),
            html.Div(id='runner-history-table', style={'display': 'none'}),
            html.Div(id='runner-plans-table', style={'display': 'none'}),
        ])
        return dbc.Container([
            hidden,
            dbc.NavbarSimple(brand=f"Panel Trenera: {username}", color="dark", dark=True, className="mb-4"),
            dbc.Row([
                # ---- LEWA KOLUMNA: lista biegaczy + dodawanie ----
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Twoi Biegacze"),
                        dbc.CardBody([
                            # Formularz dodawania biegacza
                            dbc.InputGroup([
                                dbc.Input(id='add-runner-input', placeholder="Username biegacza"),
                                dbc.Button("Dodaj", id='add-runner-btn', color="primary"),
                            ], className="mb-2"),
                            html.Div(id='add-runner-msg', className="mb-3 small"),
                            # Lista biegaczy z przyciskami usunięcia
                            html.Div(id='runners-list'),
                        ])
                    ])
                ], width=4),

                # ---- PRAWA KOLUMNA ----
                dbc.Col([
                    # Formularz zadawania treningu
                    dbc.Card([
                        dbc.CardHeader("Zadaj trening biegaczowi"),
                        dbc.CardBody([
                            dcc.Dropdown(id='select-runner', placeholder="Wybierz biegacza", className="mb-3"),
                            dbc.Input(id='p-dist', type='number', placeholder="Dystans (km)", className="mb-2"),
                            dbc.Input(id='p-time', type='number', placeholder="Czas (min)", className="mb-2"),
                            dcc.DatePickerSingle(
                                id='p-date',
                                date=date.today(),
                                display_format='YYYY-MM-DD',
                                className="mb-2"
                            ),
                            dbc.Textarea(id='p-note', placeholder="Zalecenia trenera", className="mb-2"),
                            dbc.Button("Wyślij Plan", id='plan-btn', color="success", className="w-100"),
                            html.Div(id='plan-msg', className="mt-2 small"),
                        ])
                    ], className="mb-3"),

                    # Usuwanie wpisu
                    dbc.Card([
                        dbc.CardHeader("Usuń wpis treningowy (podaj ID)"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(dbc.Input(id='delete-id', type='number', placeholder="ID"), width=8),
                                dbc.Col(dbc.Button("Usuń", id='delete-btn', color="danger", className="w-100"), width=4),
                            ]),
                            html.Div(id='delete-msg', className="mt-2 text-danger small")
                        ])
                    ], className="mb-3"),

                    # PDF
                    dbc.Card([
                        dbc.CardHeader("Raporty PDF"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(
                                    dbc.Button("Plan wybranego biegacza", id='btn-pdf-plan-single',
                                               color="info", className="w-100"),
                                    width=6),
                                dbc.Col(
                                    dbc.Button("Plany wszystkich biegaczy", id='btn-pdf-plan-all',
                                               color="secondary", className="w-100"),
                                    width=6),
                            ]),
                            html.Div(id='pdf-msg', className="mt-2 small text-danger"),
                        ])
                    ]),
                    
                    # Dzisiejsze treningi
                    dbc.Card([
                        dbc.CardHeader("Treningi dzisiaj"),
                        dbc.CardBody([
                            dcc.Interval(id='coach-refresh-today', interval=3000, n_intervals=0),
                            html.Div(id='coach-today-workouts', children="Ładowanie...")
                        ])
                    ], className="mt-3"),
                ], width=8),
            ]),
        ], fluid=True)

    # ---- LAYOUT BIEGACZA ----
    hidden = html.Div([
        dcc.Dropdown(id='select-runner', style={'display': 'none'}),
        dcc.Input(id='p-dist', style={'display': 'none'}),
        dcc.Input(id='p-time', style={'display': 'none'}),
        dcc.Input(id='p-note', style={'display': 'none'}),
        dcc.Button(id='plan-btn', style={'display': 'none'}),
        html.Div(id='plan-msg', style={'display': 'none'}),
        html.Div(id='runners-list', style={'display': 'none'}),
        dcc.Input(id='add-runner-input', style={'display': 'none'}),
        dcc.Button(id='add-runner-btn', style={'display': 'none'}),
        html.Div(id='add-runner-msg', style={'display': 'none'}),
        dcc.Button(id='btn-pdf-plan-single', style={'display': 'none'}),
        dcc.Button(id='btn-pdf-plan-all', style={'display': 'none'}),
        html.Div(id='pdf-msg', style={'display': 'none'}),
    ])
    return dbc.Container([
        hidden,
        dbc.NavbarSimple(brand=f"Panel Biegacza: {username}", color="success", dark=True, className="mb-4"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Łączny dystans"), html.H2(id='runner-total-dist')])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Liczba treningów"), html.H2(id='runner-count')])), width=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Zaraportuj bieg"),
                    dbc.CardBody([
                        dbc.Input(id='r-dist', type='number', placeholder="Dystans (km)", className="mb-2"),
                        dbc.Input(id='r-time', type='number', placeholder="Czas (min)", className="mb-2"),
                        dbc.Textarea(id='r-note', placeholder="Jak się biegło?", className="mb-2"),
                        dbc.Button("Zapisz Trening", id='r-save-btn', color="success", className="w-100"),
                    ])
                ]),
                dbc.Card([
                    dbc.CardHeader("Pobierz raport PDF"),
                    dbc.CardBody(
                        dbc.Button("Moje treningi (PDF)", id='btn-pdf', color="info", className="w-100")
                    )
                ], className="mt-3"),
            ], width=4),
            dbc.Col([
                dbc.Tabs([
                    dbc.Tab(label="Dzisiaj", children=[
                        html.Div(id='runner-today-workouts', className="mt-3")
                    ]),
                    dbc.Tab(label="Moja Historia", children=[html.Div(id='runner-history-table', className="mt-3")]),
                    dbc.Tab(label="Zadania od Trenera", children=[html.Div(id='runner-plans-table', className="mt-3")]),
                ]),
                dbc.Card([
                    dbc.CardHeader("Usuń wpis (podaj ID z tabeli)"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(dbc.Input(id='delete-id', type='number', placeholder="ID"), width=8),
                            dbc.Col(dbc.Button("Usuń", id='delete-btn', color="danger", className="w-100"), width=4),
                        ]),
                        html.Div(id='delete-msg', className="mt-2 text-danger small")
                    ])
                ], className="mt-3"),
            ], width=8),
        ]),
    ], fluid=True)


# ==================== CALLBACKI ====================

@app.callback(
    Output('page-content', 'children'),
    Input('current-page', 'data'),
    State('session-auth', 'data'),
    prevent_initial_call=False
)
def display_page(current_page, auth_data):
    if auth_data:
        return dashboard_layout(auth_data['user'], auth_data['role'])
    
    if current_page == 'register':
        return register_layout
    
    return login_layout


@app.callback(
    Output('current-page', 'data'),
    [Input('show-register-btn', 'n_clicks'),
     Input('show-login-btn', 'n_clicks'),
     Input('show-register-btn-visible', 'n_clicks'),
     Input('show-login-btn-visible', 'n_clicks')],
    prevent_initial_call=True
)
def switch_auth_page(reg_hidden_clicks, login_hidden_clicks, reg_visible_clicks, login_visible_clicks):
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
    
    if 'show-register-btn' in triggered:
        return 'register'
    elif 'show-login-btn' in triggered:
        return 'login'
    
    return dash.no_update


@app.callback(
    Output('current-page', 'data', allow_duplicate=True),
    Input('session-auth', 'data'),
    prevent_initial_call='initial_duplicate'
)
def on_login(auth_data):
    if auth_data:
        return 'dashboard'
    return 'login'


@app.callback(
    Output('session-auth', 'data'),
    Input('login-btn', 'n_clicks'),
    [State('login-user', 'value'), State('login-pass', 'value')],
    prevent_initial_call=True
)
def login(n, user, password):
    try:
        res = requests.get(f"{API}/me", auth=(user, password), verify=False)
        if res.status_code == 200:
            user_data = res.json()
            return {'user': user, 'pass': password, 'role': user_data['role']}
        return dash.no_update
    except:
        return dash.no_update


@app.callback(
    [Output('session-auth', 'data', allow_duplicate=True),
     Output('register-alert', 'children')],
    Input('register-btn', 'n_clicks'),
    [State('register-user', 'value'), State('register-pass', 'value'), State('register-role', 'value')],
    prevent_initial_call=True
)
def register(n, username, password, role):
    if not username or not password or not role:
        return dash.no_update, dbc.Alert("Wypełnij wszystkie pola!", color="warning")
    
    try:
        res = requests.post(f"{API}/register", 
                           json={"username": username, "password": password, "role": role},
                           verify=False)
        if res.status_code == 200:
            # Automatycznie zaloguj
            auth_res = requests.get(f"{API}/me", auth=(username, password), verify=False)
            if auth_res.status_code == 200:
                user_data = auth_res.json()
                return {'user': username, 'pass': password, 'role': user_data['role']}, ""
        else:
            detail = res.json().get('detail', 'Błąd rejestracji')
            return dash.no_update, dbc.Alert(detail, color="danger")
    except Exception as e:
        return dash.no_update, dbc.Alert(f"Błąd: {str(e)}", color="danger")


# ---- Callbacki trenera ----

def _fetch_runners(auth):
    res = requests.get(f"{API}/runners", auth=(auth['user'], auth['pass']), verify=False)
    return res.json() if res.status_code == 200 else []


@app.callback(
    [Output('runners-list', 'children'),
     Output('select-runner', 'options'),
     Output('add-runner-msg', 'children')],
    [Input('session-auth', 'data'),
     Input('add-runner-btn', 'n_clicks'),
     Input({'type': 'remove-runner-btn', 'index': dash.ALL}, 'n_clicks')],
    [State('add-runner-input', 'value')],
    prevent_initial_call=False
)
def manage_runners(auth, add_clicks, remove_clicks, add_username):
    if not auth or auth['role'] != "COACH":
        return [], [], ""

    msg = ""
    ctx = dash.callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ""

    # Dodawanie biegacza
    if 'add-runner-btn' in triggered and add_username:
        res = requests.post(f"{API}/runners/add",
                            json={"username": add_username},
                            auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            msg = dbc.Alert(f"Dodano biegacza: {add_username}", color="success", duration=3000)
        else:
            detail = res.json().get('detail', 'Błąd')
            msg = dbc.Alert(detail, color="danger", duration=4000)

    # Usuwanie biegacza
    if 'remove-runner-btn' in triggered and any(n for n in remove_clicks if n):
        import json
        prop = triggered.replace('.n_clicks', '')
        runner_id = json.loads(prop)['index']
        res = requests.delete(f"{API}/runners/{runner_id}",
                              auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code != 200:
            msg = dbc.Alert("Błąd usuwania biegacza", color="danger", duration=3000)

    runners = _fetch_runners(auth)
    list_items = [
        dbc.ListGroupItem([
            html.Span(f"{r['username']}  (ID: {r['id']})", className="me-auto"),
            dbc.Button("✕", id={'type': 'remove-runner-btn', 'index': r['id']},
                       color="danger", size="sm", className="ms-2")
        ], className="d-flex align-items-center justify-content-between")
        for r in runners
    ]
    options = [{'label': r['username'], 'value': r['id']} for r in runners]
    return dbc.ListGroup(list_items, flush=True), options, msg


@app.callback(
    [Output('plan-btn', 'children'), Output('plan-msg', 'children')],
    Input('plan-btn', 'n_clicks'),
    [State('select-runner', 'value'), State('p-dist', 'value'),
     State('p-time', 'value'), State('p-note', 'value'), State('p-date', 'date'), State('session-auth', 'data')],
    prevent_initial_call=True
)
def assign_workout(n, r_id, dist, time, note, plan_date, auth):
    if not r_id or not dist:
        return "Wyślij Plan", dbc.Alert("Wybierz biegacza i podaj dystans!", color="warning")
    payload = {"runner_id": r_id, "distance": dist, "time_minutes": time, "note": note, "workout_date": plan_date}
    res = requests.post(f"{API}/workouts/plan", json=payload,
                        auth=(auth['user'], auth['pass']), verify=False)
    if res.status_code == 200:
        return "Wyślij Plan", dbc.Alert("Plan wysłany!", color="success", duration=2000)
    return "Wyślij Plan", dbc.Alert("Błąd wysyłania planu", color="danger")


# PDF trenera - plan jednego biegacza
@app.callback(
    [Output("download-pdf", "data"), Output('pdf-msg', 'children')],
    [Input('btn-pdf-plan-single', 'n_clicks'),
     Input('btn-pdf-plan-all', 'n_clicks')],
    [State('session-auth', 'data'), State('select-runner', 'value')],
    prevent_initial_call=True
)
def download_coach_pdf(n_single, n_all, auth, selected_runner_id):
    if not auth:
        return dash.no_update, ""

    ctx = dash.callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ""

    if 'btn-pdf-plan-single' in triggered:
        if not selected_runner_id:
            return dash.no_update, dbc.Alert("Wybierz najpierw biegacza z listy!", color="warning")
        url = f"{API}/report/pdf/plan/{selected_runner_id}"
        fname = f"plan_biegacza_{selected_runner_id}.pdf"
    else:
        url = f"{API}/report/pdf/plan/all"
        fname = "plany_wszystkich.pdf"

    try:
        res = requests.get(url, auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return dcc.send_bytes(res.content, fname), ""
        detail = res.json().get('detail', f'Błąd {res.status_code}')
        return dash.no_update, dbc.Alert(detail, color="danger")
    except Exception as e:
        return dash.no_update, dbc.Alert(f"Błąd połączenia: {e}", color="danger")


# ---- Callbacki biegacza ----

@app.callback(
    Output('runner-today-workouts', 'children'),
    [Input('session-auth', 'data'), Input('auto-refresh', 'n_intervals')],
    prevent_initial_call=False
)
def update_runner_today_workouts(auth, n_intervals):
    if not auth or auth['role'] != "RUNNER":
        return "Brak dostępu"
    
    try:
        res = requests.get(f"{API}/workouts/today", auth=(auth['user'], auth['pass']), verify=False, timeout=3)
        if res.status_code == 200:
            workouts = res.json()
            if not workouts:
                return html.Div([
                    html.P("Dziś brak planów treningowych!", className="text-muted"),
                    html.P(f"Dzisiaj: {date.today()}", className="text-secondary small")
                ])
            
            rows = []
            for w in workouts:
                rows.append(
                    dbc.ListGroupItem([
                        html.Span(f"📍 {w['distance']} km, {w['time_minutes']} min", className="fw-bold"),
                        html.Br(),
                        html.Small(w['note'] if w['note'] else "Brak notatek"),
                        html.Br(),
                        dbc.Button("✓ Ukończono", id={'type': 'complete-workout-btn', 'index': w['id']},
                                  color="success", size="sm", className="mt-2")
                    ], className="p-3")
                )
            
            return dbc.ListGroup(rows)
        return "Błąd pobierania treningów"
    except:
        return "Brak połączenia"


@app.callback(
    Output('runner-today-workouts', 'children', allow_duplicate=True),
    Input({'type': 'complete-workout-btn', 'index': dash.ALL}, 'n_clicks'),
    State('session-auth', 'data'),
    prevent_initial_call=True
)
def complete_today_workout(n_clicks, auth):
    if not auth or not n_clicks or not any(n_clicks):
        return dash.no_update
    
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ""
    
    if triggered:
        import json
        prop = triggered.replace('.n_clicks', '')
        workout_id = json.loads(prop)['index']
        
        res = requests.patch(f"{API}/workouts/{workout_id}/complete",
                            auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            # Odśwież listę
            return dash.callback_context.outputs_list[0]
    
    return dash.no_update


@app.callback(
    [Output('runner-total-dist', 'children'),
     Output('runner-count', 'children'),
     Output('runner-history-table', 'children'),
     Output('runner-plans-table', 'children')],
    [Input('session-auth', 'data'), Input('r-save-btn', 'n_clicks'), Input('auto-refresh', 'n_intervals')],
    prevent_initial_call=False
)
def update_runner_data(auth, n, n_intervals):
    if not auth or auth['role'] != "RUNNER":
        return dash.no_update

    try:
        stats_res = requests.get(f"{API}/stats", auth=(auth['user'], auth['pass']), verify=False, timeout=3)
        stats = stats_res.json() if stats_res.status_code == 200 else {"total_distance": 0, "count": 0}

        workouts_res = requests.get(f"{API}/workouts", auth=(auth['user'], auth['pass']), verify=False, timeout=3)

        if workouts_res.status_code == 200:
            raw_data = workouts_res.json()
            if not raw_data:
                return f"{stats['total_distance']} km", str(stats['count']), "Brak historii", "Brak zadań od trenera"

            df = pd.DataFrame(raw_data)
            df['is_planned'] = df['is_planned'].fillna(False).astype(bool)

            history_df = df[~df['is_planned']]
            hist_table = (
                dbc.Table.from_dataframe(history_df[['id', 'distance', 'time_minutes', 'note']],
                                         striped=True, hover=True)
                if not history_df.empty else "Nie biegasz? Czas zacząć!"
            )

            plans_df = df[df['is_planned']]
            plan_table = (
                dbc.Table.from_dataframe(plans_df[['id', 'distance', 'time_minutes', 'note']],
                                          striped=True, color="info")
                if not plans_df.empty else "Trener jeszcze nic nie zaplanował."
            )
            return f"{stats['total_distance']} km", str(stats['count']), hist_table, plan_table

        return "Błąd", "Błąd", "Błąd autoryzacji", "Błąd autoryzacji"
    except Exception as e:
        return "!", "!", "Brak połączenia z API", str(e)


@app.callback(
    Output('r-save-btn', 'children'),
    Input('r-save-btn', 'n_clicks'),
    [State('r-dist', 'value'), State('r-time', 'value'),
     State('r-note', 'value'), State('session-auth', 'data')],
    prevent_initial_call=True
)
def save_runner_workout(n, dist, time, note, auth):
    if not dist or not time:
        return "Zapisz Trening"
    requests.post(f"{API}/workouts",
                  json={"distance": dist, "time_minutes": time, "note": note},
                  auth=(auth['user'], auth['pass']), verify=False)
    return "Zapisano!"


# ---- Callbacki trenera ----

@app.callback(
    Output('coach-today-workouts', 'children'),
    [Input('session-auth', 'data'), Input('coach-refresh-today', 'n_intervals')],
    prevent_initial_call=False
)
def update_coach_today_workouts(auth, n_intervals):
    if not auth or auth['role'] != "COACH":
        return "Brak dostępu"
    
    try:
        # Pobierz listę biegaczy
        runners_res = requests.get(f"{API}/runners", auth=(auth['user'], auth['pass']), verify=False, timeout=3)
        if runners_res.status_code != 200:
            return "Błąd pobierania listy biegaczy"
        
        runners = runners_res.json()
        if not runners:
            return html.P("Nie masz jeszcze biegaczy w grupie", className="text-muted")
        
        sections = []
        for runner in runners:
            res = requests.get(f"{API}/workouts/runner/{runner['id']}/today", 
                              auth=(auth['user'], auth['pass']), verify=False, timeout=3)
            
            workouts = res.json() if res.status_code == 200 else []
            
            if not workouts:
                sections.append(
                    html.Div([
                        html.H6(f"👤 {runner['username']}", className="mb-2 text-muted"),
                        html.Small("Brak treningów na dzisiaj", className="text-secondary")
                    ], className="mb-3 p-2 border-start border-secondary")
                )
            else:
                rows = []
                for w in workouts:
                    completed_badge = dbc.Badge("✓ Ukończono", color="success", className="ms-2") if w['completed'] else ""
                    rows.append(
                        dbc.ListGroupItem([
                            html.Span(f"📍 {w['distance']} km, {w['time_minutes']} min", className="fw-bold"),
                            completed_badge,
                            html.Br(),
                            html.Small(w['note'] if w['note'] else "Brak notatek", className="text-secondary")
                        ], className="p-2")
                    )
                
                sections.append(
                    html.Div([
                        html.H6(f"👤 {runner['username']}", className="mb-2"),
                        dbc.ListGroup(rows, flush=True)
                    ], className="mb-3 p-2 border-start border-primary border-3")
                )
        
        return html.Div(sections) if sections else "Brak treningów"
    except Exception as e:
        return f"Błąd: {str(e)}"


@app.callback(
    Output('delete-msg', 'children'),
    Input('delete-btn', 'n_clicks'),
    [State('delete-id', 'value'), State('session-auth', 'data')],
    prevent_initial_call=True
)
def delete_action(n, w_id, auth):
    if not w_id:
        return "Podaj ID!"
    res = requests.delete(f"{API}/workouts/{w_id}", auth=(auth['user'], auth['pass']), verify=False)
    if res.status_code == 200:
        return dbc.Alert(f"Usunięto wpis {w_id}.", color="success", duration=3000)
    if res.status_code == 403:
        return dbc.Alert("Brak uprawnień!", color="danger")
    return dbc.Alert(f"Błąd: {res.status_code}", color="danger")


# PDF biegacza - jego zrealizowane treningi
@app.callback(
    Output("download-pdf", "data", allow_duplicate=True),
    Input("btn-pdf", "n_clicks"),
    State('session-auth', 'data'),
    prevent_initial_call=True
)
def download_runner_pdf(n, auth):
    if not auth:
        return dash.no_update
    try:
        me = requests.get(f"{API}/me", auth=(auth['user'], auth['pass']), verify=False).json()
        res = requests.get(f"{API}/report/pdf/runner/{me['id']}",
                           auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return dcc.send_bytes(res.content, f"raport_{auth['user']}.pdf")
        detail = res.json().get('detail', f'Błąd {res.status_code}')
        print(f"PDF błąd: {detail}")
        return dash.no_update
    except Exception as e:
        print(f"PDF wyjątek: {e}")
        return dash.no_update


if __name__ == '__main__':
    app.run(debug=True, port=8050)