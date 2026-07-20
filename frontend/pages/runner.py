import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import requests
import pandas as pd
from datetime import date

API = "https://192.168.43.66:8000"


# layut

def _get_today_panel_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Zadane treningi od trenera na dziś"),
                dbc.CardBody(html.Div(id='runner-today-workouts'))
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Zaraportuj dzisiejszy bieg (trening własny)"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(dbc.Input(id='r-dist', type='number', placeholder="Dystans (km)", className="mb-2"),
                                width=6),
                        dbc.Col(dbc.Input(id='r-time', type='number', placeholder="Czas (min)", className="mb-2"),
                                width=6),
                    ]),

                    dbc.Label("Tempo i prędkość biegu (uzupełniają się automatycznie):"),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='r-pace-minkm', type='number', step=0.01, placeholder="Tempo (min/km)",
                                          className="mb-2"), width=6),
                        dbc.Col(dbc.Input(id='r-speed-kmh', type='number', step=0.01, placeholder="Prędkość (km/h)",
                                          className="mb-2"), width=6),
                    ], className="mb-3"),

                    dbc.Textarea(id='r-note', placeholder="Jak się biegło?", className="mb-3"),
                    dbc.Button("Zapisz Trening", id='r-save-btn', color="success", className="w-100"),
                    html.Div(id='r-save-msg', className="mt-2 text-success small")
                ])
            ])
        ], width=6)
    ])


def _get_history_panel_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Filtrowanie historii treningów"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Zakres dat:"),
                            dcc.DatePickerRange(
                                id='runner-history-date-range',
                                start_date=None,
                                end_date=date.today(),
                                display_format='YYYY-MM-DD',
                                className="mb-2 d-block"
                            )
                        ], width=8),
                        dbc.Col([
                            dbc.Label("Eksport PDF:"),
                            dbc.Button("Pobierz raport (PDF)", id='btn-pdf', color="info", className="w-100")
                        ], width=4, className="d-flex flex-column justify-content-end")
                    ], className="align-items-end mb-3"),
                    html.Div(id='runner-history-table')
                ])
            ])
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Usuń wpis (podaj ID z tabeli)"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(dbc.Input(id='runner-delete-id', type='number', placeholder="ID"), width=8),
                        dbc.Col(dbc.Button("Usuń", id='runner-delete-btn', color="danger", className="w-100"), width=4),
                    ]),
                    html.Div(id='runner-delete-msg', className="mt-2 text-danger small")
                ])
            ])
        ], width=4)
    ])


def _get_stats_panel_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Twoje statystyki"),
                dbc.CardBody([
                    dcc.DatePickerRange(
                        id='runner-stats-date-range',
                        start_date=None,
                        end_date=date.today(),
                        display_format='YYYY-MM-DD',
                        className="mb-3 d-block"
                    ),
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Łączny dystans", className="small text-muted py-1"),
                            dbc.CardBody(html.H4(id='runner-total-dist', children="0.0 km"),
                                         className="py-2 text-center")
                        ]), width=6),
                        dbc.Col(dbc.Card([
                            dbc.CardHeader("Liczba treningów", className="small text-muted py-1"),
                            dbc.CardBody(html.H4(id='runner-count', children="0"), className="py-2 text-center")
                        ]), width=6),
                    ])
                ])
            ])
        ], width=5),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Komunikacja z trenerem"),
                dbc.CardBody([
                    html.Div(
                        id='runner-chat-box',
                        style={"height": "250px", "overflowY": "scroll", "border": "1px solid #ddd", "padding": "10px",
                               "backgroundColor": "#fff"},
                        className="mb-2 rounded"
                    ),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='runner-chat-text', placeholder="Napisz do trenera"), width=9),
                        dbc.Col(dbc.Button("Wyślij", id='runner-chat-send-btn', color="primary", className="w-100"),
                                width=3)
                    ])
                ])
            ])
        ], width=7)
    ])


def layout(username):
    return dbc.Container([
        dcc.Store(id='runner-active-panel', data='today'),
        dcc.Store(id='runner-coach-id-store', data=None),
        dcc.Store(id='runner-my-id-store', data=None),
        dcc.Interval(id='runner-chat-refresh', interval=5000, n_intervals=0),

        dbc.NavbarSimple(
            brand=f"Panel Biegacza: {username}",
            color="success",
            dark=True,
            className="mb-4",
            children=[dbc.Button("Wyloguj", id='logout-btn', color="secondary", size="sm")]
        ),
        dbc.Row([
            dbc.Col(
                dbc.ButtonGroup([
                    dbc.Button("Dzisiejsze treningi", id='btn-runner-panel-today', color="success", outline=True,
                               className="px-4"),
                    dbc.Button("Moja Historia treningów", id='btn-runner-panel-history', color="success", outline=True,
                               className="px-4"),
                    dbc.Button("Statystyki treningów i kontakt z trenerem", id='btn-runner-panel-stats', color="success", outline=True,
                               className="px-4"),
                ], className="w-100"),
                width=12, className="mb-4 text-center"
            )
        ]),

        html.Div(id='runner-panel-today-container', children=_get_today_panel_layout(), style={"display": "block"}),
        html.Div(id='runner-panel-history-container', children=_get_history_panel_layout(), style={"display": "none"}),
        html.Div(id='runner-panel-stats-container', children=_get_stats_panel_layout(), style={"display": "none"}),
    ], fluid=True)

def register_callbacks(app):
    # Nawigacja paneli
    @app.callback(
        Output('runner-active-panel', 'data'),
        [Input('btn-runner-panel-today', 'n_clicks'),
         Input('btn-runner-panel-history', 'n_clicks'),
         Input('btn-runner-panel-stats', 'n_clicks')],
        prevent_initial_call=True
    )
    def switch_runner_panel(today, history, stats):
        ctx = callback_context
        if not ctx.triggered:
            return 'today'
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'btn-runner-panel-history':
            return 'history'
        if button_id == 'btn-runner-panel-stats':
            return 'stats'
        return 'today'

    @app.callback(
        [Output('runner-panel-today-container', 'style'),
         Output('runner-panel-history-container', 'style'),
         Output('runner-panel-stats-container', 'style')],
        Input('runner-active-panel', 'data')
    )
    def toggle_runner_containers(active_panel):
        today_s = {"display": "block"} if active_panel == 'today' else {"display": "none"}
        history_s = {"display": "block"} if active_panel == 'history' else {"display": "none"}
        stats_s = {"display": "block"} if active_panel == 'stats' else {"display": "none"}
        return today_s, history_s, stats_s

    # Pobieranie profili
    @app.callback(
        [Output('runner-coach-id-store', 'data'),
         Output('runner-my-id-store', 'data')],
        Input('session-auth', 'data'),
        prevent_initial_call=False
    )
    def fetch_runner_identities(auth):
        if not auth or auth['role'] != "RUNNER":
            return None, None
        try:
            me = requests.get(f"{API}/me", auth=(auth['user'], auth['pass']), verify=False).json()
            return me.get('coach_id'), me.get('id')
        except Exception:
            return None, None

    # Synchronizacja tempa i prędkości
    @app.callback(
        [Output('r-pace-minkm', 'value'),
         Output('r-speed-kmh', 'value'),
         Output('r-save-msg', 'children', allow_duplicate=True)],
        [Input('r-dist', 'value'),
         Input('r-time', 'value'),
         Input('r-pace-minkm', 'value'),
         Input('r-speed-kmh', 'value')],
        prevent_initial_call=True
    )
    def sync_pace_speed_runner(dist, time, pace, speed):
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # yliczanie z dystansu i czasu
        if trigger_id in ['r-dist', 'r-time']:
            if dist and time and dist > 0 and time > 0:
                calc_pace = round(time / dist, 2)
                calc_speed = round((dist / time) * 60, 2)
                if calc_speed < 3 or calc_speed > 20:
                    return calc_pace, calc_speed, dbc.Alert(
                        "Ostrzeżenie: Wyliczona prędkość wykracza poza bezpieczny zakres (3-20 km/h)!", color="warning")
                return calc_pace, calc_speed, ""
            return dash.no_update, dash.no_update, dash.no_update

        # Tempo -> Prędkość
        if trigger_id == 'r-pace-minkm':
            if pace and pace > 0:
                calc_speed = round(60 / pace, 2)
                if calc_speed < 3 or calc_speed > 20:
                    return pace, calc_speed, dbc.Alert("Błąd: Prędkość musi wynosić od 3 km/h do 20 km/h!",
                                                       color="danger")
                return pace, calc_speed, ""
            return None, None, ""

        # Prędkość -> Tempo
        if trigger_id == 'r-speed-kmh':
            if speed and speed > 0:
                calc_pace = round(60 / speed, 2)
                if speed < 3 or speed > 20:
                    return calc_pace, speed, dbc.Alert("Błąd: Prędkość musi wynosić od 3 km/h do 20 km/h!",
                                                       color="danger")
                return calc_pace, speed, ""
            return None, None, ""

        return dash.no_update, dash.no_update, dash.no_update

    #plany od trenera
    @app.callback(
        Output('runner-today-workouts', 'children'),
        [Input('session-auth', 'data'), Input('runner-update-trigger', 'data')],
        prevent_initial_call=False
    )
    def update_runner_today(auth, _):
        if not auth or auth['role'] != "RUNNER":
            return ""
        try:
            res = requests.get(f"{API}/workouts/today", auth=(auth['user'], auth['pass']), verify=False)
            workouts = res.json() if res.status_code == 200 else []
            if not workouts:
                return html.P("Dziś brak planów treningowych. Możesz odpocząć lub wpisać trening własny.",
                              className="text-muted mt-2 small")

            elements = []
            for w in workouts:
                int_inf = f"Interwał {w['interval_repeats']}x{w['interval_distance_meters']}m (przerwa: {w['interval_recovery'] or '-'}) | " if w.get(
                    'is_interval') else ""
                pace_inf = f" (Docelowe tempo: {w['target_pace']})" if w.get('target_pace') else ""
                elements.append(dbc.ListGroupItem([
                    html.Span(f"{w['distance']} km, {w['time_minutes']} min{pace_inf}", className="fw-bold small"),
                    html.Br(),
                    html.Small(f"{int_inf}{w.get('note') or 'Brak notatek'}", className="text-secondary small"),
                    html.Br(),
                    dbc.Button("Ukończono", id={'type': 'complete-workout-btn', 'index': w['id']}, color="success",
                               size="sm", className="mt-2 py-0")
                ], className="p-3"))
            return dbc.ListGroup(elements)
        except Exception:
            return "Brak połączenia z API"

    #oznaczenie planu trenera jako zrealizowany
    @app.callback(
        Output('runner-update-trigger', 'data', allow_duplicate=True),
        Input({'type': 'complete-workout-btn', 'index': dash.ALL}, 'n_clicks'),
        [State('session-auth', 'data'), State('runner-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def complete_workout(n_clicks, auth, current_trigger):
        if not auth or not any(n for n in n_clicks if n):
            return dash.no_update
        import json
        triggered = callback_context.triggered[0]['prop_id']
        workout_id = json.loads(triggered.replace('.n_clicks', ''))['index']
        requests.patch(f"{API}/workouts/{workout_id}/complete", auth=(auth['user'], auth['pass']), verify=False)
        return (current_trigger or 0) + 1


    @app.callback(
        [Output('r-save-msg', 'children'),
         Output('runner-update-trigger', 'data', allow_duplicate=True),
         Output('r-dist', 'value'),
         Output('r-time', 'value'),
         Output('r-pace-minkm', 'value', allow_duplicate=True),
         Output('r-speed-kmh', 'value', allow_duplicate=True),
         Output('r-note', 'value')],
        Input('r-save-btn', 'n_clicks'),
        [State('r-dist', 'value'), State('r-time', 'value'), State('r-pace-minkm', 'value'),
         State('r-speed-kmh', 'value'),
         State('r-note', 'value'), State('session-auth', 'data'),
         State('runner-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def save_runner_workout(n, dist, time, pace_minkm, speed_kmh, note, auth, current_trigger):
        if not dist or not time:
            return "Wprowadź dystans i czas!", dash.no_update, dist, time, pace_minkm, speed_kmh, note

        if speed_kmh and (speed_kmh < 3 or speed_kmh > 20):
            return "Błąd zapisu: Dozwolona prędkość musi mieścić się w granicach 3 - 20 km/h!", dash.no_update, dist, time, pace_minkm, speed_kmh, note

        pace_str = f"{pace_minkm} min/km ({speed_kmh} km/h)" if pace_minkm else None

        requests.post(f"{API}/workouts",
                      json={"distance": dist, "time_minutes": time, "target_pace": pace_str, "note": note},
                      auth=(auth['user'], auth['pass']), verify=False)
        return "Twój trening został zapisany!", (current_trigger or 0) + 1, None, None, None, None, ""

    @app.callback(
        Output('runner-history-table', 'children'),
        [Input('session-auth', 'data'),
         Input('runner-update-trigger', 'data'),
         Input('runner-history-date-range', 'start_date'),
         Input('runner-history-date-range', 'end_date')],
        prevent_initial_call=False
    )
    def update_runner_history_table(auth, _, start_date, end_date):
        if not auth or auth['role'] != "RUNNER":
            return ""

        try:
            raw = requests.get(f"{API}/workouts", auth=(auth['user'], auth['pass']), verify=False).json()
            if not raw:
                return "Brak historii treningów."

            df = pd.DataFrame(raw)
            df['is_planned'] = df['is_planned'].fillna(False).astype(bool)

            # Pobieramy absolutnie wszystkie wpisy z bazy danych
            hist_df = df.copy()
            hist_df['workout_date'] = pd.to_datetime(hist_df['workout_date']).dt.date
            if start_date:
                hist_df = hist_df[hist_df['workout_date'] >= pd.to_datetime(start_date).date()]
            if end_date:
                hist_df = hist_df[hist_df['workout_date'] <= pd.to_datetime(end_date).date()]

            if hist_df.empty:
                return "Brak treningów w wybranym przedziale czasu."

            hist_df = hist_df.sort_values(by='workout_date', ascending=False)
            hist_df['Lp.'] = range(1, len(hist_df) + 1)

            # określanie typu i statusu ukończenia
            hist_df['Typ'] = hist_df.apply(lambda r: "Zadanie" if r['is_planned'] else "Własny", axis=1)
            hist_df['Status'] = hist_df.apply(lambda r: "Ukończono" if (r['completed'] or not r['is_planned']) else "Oczekuje", axis=1)

            # mapowanie kolumn z uwzględnieniem danych o interwałach
            def format_note_field(row):
                desc = row['note'] or ""
                if row['is_interval']:
                    desc = f"Interwał {row['interval_repeats']}x{row['interval_distance_meters']}m (przerwa: {row['interval_recovery'] or '-'}) | " + desc
                return desc if desc else "-"

            hist_df['Komentarz / Notatki / Interwały'] = hist_df.apply(format_note_field, axis=1)

            return dbc.Table.from_dataframe(
                hist_df[['Lp.', 'id', 'workout_date', 'distance', 'time_minutes', 'target_pace', 'Typ', 'Status', 'Komentarz / Notatki / Interwały']].rename(columns={
                    "Lp.": "Lp.", "id": "ID bazy", "workout_date": "Data", "distance": "Dystans (km)",
                    "time_minutes": "Czas (min)", "target_pace": "Tempo", "Typ": "Typ", "Status": "Status"
                }), striped=True, hover=True
            )
        except Exception as e:
            return f"Błąd ładowania danych: {e}"

    # isuwanie treningu własnego
    @app.callback(
        [Output('runner-delete-msg', 'children'),
         Output('runner-update-trigger', 'data', allow_duplicate=True)],
        Input('runner-delete-btn', 'n_clicks'),
        [State('runner-delete-id', 'value'), State('session-auth', 'data'),
         State('runner-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def runner_delete_action(n, w_id, auth, runner_trig):
        if not w_id:
            return "Podaj ID!", dash.no_update
        res = requests.delete(f"{API}/workouts/{w_id}", auth=(auth['user'], auth['pass']), verify=False)
        if res.status_code == 200:
            return dbc.Alert(f"Usunięto wpis o ID {w_id}.", color="success", duration=3000), (runner_trig or 0) + 1
        return dbc.Alert("Wpis nie istnieje lub należy do kogoś innego", color="danger"), dash.no_update

    #PDF
    @app.callback(
        Output("download-pdf", "data", allow_duplicate=True),
        Input("btn-pdf", "n_clicks"),
        [State('session-auth', 'data'), State('runner-my-id-store', 'data')],
        prevent_initial_call=True
    )
    def download_runner_pdf(n, auth, my_id):
        if not auth or not my_id:
            return dash.no_update
        try:
            res = requests.get(f"{API}/report/pdf/runner/{my_id}", auth=(auth['user'], auth['pass']), verify=False)
            if res.status_code == 200:
                return dcc.send_bytes(res.content, f"raport_{auth['user']}.pdf")
        except Exception:
            pass
        return dash.no_update

    # statystyki z filtrami dat
    @app.callback(
        [Output('runner-total-dist', 'children'),
         Output('runner-count', 'children')],
        [Input('runner-stats-date-range', 'start_date'),
         Input('runner-stats-date-range', 'end_date'),
         Input('runner-my-id-store', 'data'),
         Input('runner-update-trigger', 'data')],
        State('session-auth', 'data'),
        prevent_initial_call=False
    )
    def update_runner_stats(start_date, end_date, my_id, _, auth):
        if not auth or not my_id:
            return "0.0 km", "0"

        url = f"{API}/stats/runner/{my_id}"
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        try:
            res = requests.get(url, params=params, auth=(auth['user'], auth['pass']), verify=False)
            if res.status_code == 200:
                data = res.json()
                return f"{data.get('total_distance', 0)} km", str(data.get('count', 0))
        except Exception:
            pass
        return "0.0 km", "0"

    # czatbiegacza
    @app.callback(
        Output('runner-chat-box', 'children'),
        [Input('runner-coach-id-store', 'data'),
         Input('runner-chat-refresh', 'n_intervals'),
         Input('runner-update-trigger', 'data')],
        State('session-auth', 'data'),
        prevent_initial_call=False
    )
    def load_runner_chat(coach_id, n, _, auth):
        if not auth or not coach_id:
            return html.Small("Funkcja czatu z trenerem jest obecnie uśpiona.", className="text-muted")

        try:
            res = requests.get(f"{API}/messages/thread/{coach_id}", auth=(auth['user'], auth['pass']), verify=False)
            if res.status_code == 200:
                msgs = res.json()
                if not msgs:
                    return html.Small("Brak wiadomości z Twoim trenerem. Weź napisz coś!", className="text-secondary")

                chat_elements = []
                for m in msgs:
                    is_me = (m['sender_id'] != coach_id)
                    align = "text-end" if is_me else "text-start"
                    color = "#e2f0d9" if is_me else "#f2f2f2"

                    chat_elements.append(html.Div([
                        html.Div(m['text'], style={
                            "padding": "6px 12px", "borderRadius": "12px",
                            "backgroundColor": color, "display": "inline-block",
                            "maxWidth": "70%", "textAlign": "left"
                        }),
                        html.Div(html.Small(m['created_at'].replace('T', ' ')[:16], className="text-muted",
                                            style={"fontSize": "10px"}), className="mt-1")
                    ], className=f"mb-2 {align} d-flex flex-column align-items-{'end' if is_me else 'start'}"))
                return chat_elements
        except Exception:
            pass
        return "Błąd pobierania wiadomości."

    #wysyłanie wiadomości do trenera
    @app.callback(
        [Output('runner-chat-text', 'value'),
         Output('runner-update-trigger', 'data', allow_duplicate=True)],
        Input('runner-chat-send-btn', 'n_clicks'),
        [State('runner-chat-text', 'value'),
         State('runner-coach-id-store', 'data'),
         State('session-auth', 'data'),
         State('runner-update-trigger', 'data')],
        prevent_initial_call=True
    )
    def send_runner_msg(n, text, coach_id, auth, current_trigger):
        if not auth or not coach_id or not text or not text.strip():
            return dash.no_update, dash.no_update
        try:
            requests.post(f"{API}/messages", json={"receiver_id": coach_id, "text": text},
                          auth=(auth['user'], auth['pass']), verify=False)
            return "", (current_trigger or 0) + 1
        except Exception:
            return text, dash.no_update