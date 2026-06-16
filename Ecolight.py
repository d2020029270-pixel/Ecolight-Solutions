from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import requests
import os

# ==========================
# CONFIG
# ==========================

app = Flask(__name__)

EMPRESA = "EcoLight Solutions"
DB_NAME = "ecolight.db"
CIDADE = "Passo Fundo"


# ==========================
# BANCO
# ==========================

def get_conn():
    return sqlite3.connect(DB_NAME)


def criar_banco():

    conn = get_conn()

    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS leituras(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        luz INTEGER,
        data_hora TEXT
    )
    """)

    conn.commit()

    conn.close()


criar_banco()


# ==========================
# SALVAR
# ==========================

def salvar_leitura(luz):

    conn = get_conn()

    c = conn.cursor()

    horario = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    c.execute(
        """
        INSERT INTO leituras
        (luz,data_hora)

        VALUES (?,?)
        """,
        (luz, horario)
    )

    conn.commit()

    conn.close()


# ==========================
# DASHBOARD
# ==========================

def obter_dados():

    conn = get_conn()

    c = conn.cursor()

    c.execute(
        "SELECT COUNT(*) FROM leituras"
    )

    total = c.fetchone()[0]

    c.execute("""
        SELECT luz,data_hora
        FROM leituras
        ORDER BY id DESC
        LIMIT 1
    """)

    ultima = c.fetchone()

    conn.close()

    if ultima:

        luz = ultima[0]

        horario = ultima[1]

    else:

        luz = 0

        horario = "-"

    consumo = round(
        total * 0.00045,
        3
    )

    economia = max(
        0,
        min(
            100,
            round(
                (1000 - luz) / 10
            )
        )
    )

    return {
        "luz": luz,
        "horario": horario,
        "consumo": consumo,
        "economia": economia
    }


# ==========================
# CLIMA
# ==========================

def obter_clima():

    try:

        r = requests.get(
            f"https://wttr.in/{CIDADE}?format=j1",
            timeout=5
        )

        dados = r.json()

        atual = dados["current_condition"][0]

        return {

            "temp": atual["temp_C"],

            "umidade": atual["humidity"],

            "descricao":
            atual["weatherDesc"][0]["value"]

        }

    except:

        return {

            "temp": "--",

            "umidade": "--",

            "descricao": "Indisponível"

        }


# ==========================
# APIs
# ==========================

@app.route("/api/cards")
def cards():

    return jsonify(
        obter_dados()
    )


@app.route("/api/clima")
def clima():

    return jsonify(
        obter_clima()
    )


# ==========================
# HOME
# ==========================

@app.route("/")
def home():

    d = obter_dados()

    return f"""

<html>

<head>

<title>{EMPRESA}</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body{{
margin:0;
font-family:Segoe UI;
background:#eef3fb;
}}

header{{
padding:30px;
background:#1565c0;
color:white;
text-align:center;
}}

.cards{{
display:grid;
grid-template-columns:
repeat(auto-fit,minmax(250px,1fr));
gap:20px;
padding:25px;
}}

.card{{
background:white;
padding:25px;
border-radius:20px;
}}

.valor{{
font-size:32px;
font-weight:bold;
color:#1565c0;
}}

.box{{
background:white;
margin:25px;
padding:25px;
border-radius:20px;
}}

</style>

</head>

<body>

<header>

<h1>🌿 {EMPRESA}</h1>

</header>

<div class="cards">

<div class="card">

Sistema

<div class="valor">

🟢 Online

</div>

</div>

<div class="card">

Luminosidade

<div class="valor" id="luz">

{d["luz"]}

</div>

</div>

<div class="card">

Consumo

<div class="valor" id="consumo">

{d["consumo"]}

kWh

</div>

</div>

<div class="card">

Economia

<div class="valor" id="economia">

{d["economia"]}%

</div>

</div>

<div class="card">

🌤 Clima

<div class="valor" id="temp">

--

</div>

<div id="clima">

Carregando

</div>

</div>

</div>

<div class="box">

<canvas id="grafico"></canvas>

</div>

<script>

let chart;

async function atualizar(){{

let r=
await fetch("/api/cards");

let d=
await r.json();

luz.innerText=d.luz;

consumo.innerText=
d.consumo+" kWh";

economia.innerText=
d.economia+"%";

let c=
await fetch("/api/clima");

let clima=
await c.json();

temp.innerText=
clima.temp+"°C";

document
.getElementById("clima")
.innerText=

clima.descricao+
" | "+
clima.umidade+"%";

}}

atualizar();

setInterval(
atualizar,
5000
);

</script>

</body>

</html>

"""


# ==========================
# ESP8266
# ==========================

@app.route("/dados")
def receber():

    luz = request.args.get("luz")

    if not luz:

        return "SEM DADOS"

    salvar_leitura(
        int(luz)
    )

    return "OK"


# ==========================
# START
# ==========================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )

    )
