from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import requests
import os

app = Flask(__name__)

EMPRESA = "EcoLight Solutions"
DB_NAME = "ecolight.db"
CIDADE = "Itajuba MG"


# ======================
# BANCO
# ======================

def get_conn():
    return sqlite3.connect(DB_NAME)


def criar_banco():

    conn = get_conn()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS leituras(
        id INTEGER PRIMARY KEY,
        luz INTEGER,
        data_hora TEXT
    )
    """)

    conn.commit()

    conn.close()


criar_banco()


# ======================
# SALVAR
# ======================

def salvar_leitura(luz):

    conn = get_conn()

    conn.execute(
        """
        INSERT INTO leituras
        (luz,data_hora)

        VALUES (?,?)
        """,
        (
            luz,
            datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        )
    )

    conn.commit()

    conn.close()


# ======================
# DASHBOARD
# ======================

def obter_dados():

    conn = get_conn()

    c = conn.cursor()

    c.execute("""
    SELECT luz,data_hora
    FROM leituras
    ORDER BY id DESC
    LIMIT 1
    """)

    ultima = c.fetchone()

    c.execute(
        "SELECT COUNT(*) FROM leituras"
    )

    total = c.fetchone()[0]

    conn.close()

    if ultima:

        luz = ultima[0]

        horario = ultima[1]

        try:

            diff = (
                datetime.now()
                -
                datetime.strptime(
                    horario,
                    "%d/%m/%Y %H:%M:%S"
                )
            ).seconds

            online = diff < 15

        except:

            online = False

    else:

        luz = 0
        horario = "-"
        online = False

    return {

        "luz": luz,

        "horario": horario,

        "consumo":
        round(
            total*0.00045,
            3
        ),

        "economia":
        max(
            0,
            min(
                100,
                round(
                    (1000-luz)/10
                )
            )
        ),

        "online":
        online

    }


# ======================
# CLIMA
# ======================

def obter_clima():

    try:

        r = requests.get(
            f"https://wttr.in/{CIDADE}?format=j1",
            timeout=5
        )

        dados = r.json()

        atual = dados["current_condition"][0]

        chuva = dados[
            "weather"
        ][0][
            "hourly"
        ][0].get(
            "chanceofrain",
            "--"
        )

        return {

            "temp":
            atual["temp_C"],

            "descricao":
            atual[
                "weatherDesc"
            ][0]["value"],

            "umidade":
            atual["humidity"],

            "chuva":
            chuva

        }

    except:

        return {

            "temp":"--",
            "descricao":"Sem dados",
            "umidade":"--",
            "chuva":"--"

        }


# ======================
# APIs
# ======================

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


# ======================
# HOME
# ======================

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
text-align:center;

background:
linear-gradient(
135deg,
#1565c0,
#1e88e5
);

color:white;
}}

.cards{{
display:grid;

grid-template-columns:
repeat(auto-fit,minmax(240px,1fr));

gap:20px;

padding:25px;
}}

.card{{
background:white;

padding:25px;

border-radius:20px;

box-shadow:
0 8px 20px rgba(0,0,0,.08);
}}

.valor{{
font-size:30px;
font-weight:bold;
color:#1565c0;
}}

.online{{
color:#00c853;
}}

.offline{{
color:#d50000;
}}

.box{{
margin:25px;

background:white;

padding:25px;

border-radius:20px;
}}

</style>

</head>

<body>

<header>

<h1>🌿 EcoLight Solutions</h1>

<p>Monitoramento Inteligente</p>

</header>

<div class="cards">

<div class="card">
Sistema
<div id="status"></div>
</div>

<div class="card">
☀ Luminosidade
<div class="valor" id="luz">
{d["luz"]}
</div>
</div>

<div class="card">
⚡ Consumo
<div class="valor" id="consumo">
{d["consumo"]} kWh
</div>
</div>

<div class="card">
🌱 Economia
<div class="valor" id="economia">
{d["economia"]}%
</div>
</div>

<div class="card">
🌤 Clima
<div class="valor" id="temp">
--
</div>
<div id="clima"></div>
</div>

<div class="card">
🔔 Notificações
<div id="alerta">
Normal
</div>
</div>

</div>

<div class="box">

<h2>📈 Histórico</h2>

<canvas id="grafico"></canvas>

</div>

<script>

let chart;

async function atualizar(){{

let r=
await fetch(
"/api/cards"
);

let d=
await r.json();

luz.innerText=d.luz;

consumo.innerText=
d.consumo+" kWh";

economia.innerText=
d.economia+"%";


status.innerHTML=
d.online
?
'<span class="online">🟢 Online</span>'
:
'<span class="offline">🔴 Offline</span>';


// CLIMA

let c=
await fetch(
"/api/clima"
);

let clima=
await c.json();

temp.innerText=
clima.temp+"°C";

document
.getElementById(
"clima"
)
.innerHTML=

clima.descricao+

"<br>☔ "+

clima.chuva+

"%";


// ALERTAS

if(
clima.chuva>70
){{
alerta.innerText=
"☔ Alta chance de chuva";
}}

else if(
d.luz<300
){{
alerta.innerText=
"⚠ Baixa luminosidade";
}}

else{{
alerta.innerText=
"✓ Ambiente normal";
}}


// GRAFICO

let g=
await fetch(
"/grafico"
);

let dados=
await g.json();

if(!chart){{

chart=
new Chart(
grafico,
{{
type:"line",

data:{{
labels:
dados.labels,

datasets:[{{
label:
"Luminosidade",

data:
dados.valores,

fill:true,

tension:.4
}}]
}}
}}
);

}}

else{{

chart.data.labels=
dados.labels;

chart.data.datasets[0].data=
dados.valores;

chart.update();

}}

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


# ======================
# RECEBER ESP
# ======================

@app.route("/dados")
def dados():

    luz = request.args.get("luz")

    if luz is None:
        return "SEM DADOS"

    try:

        salvar_leitura(
            int(luz)
        )

        return "OK"

    except Exception as e:

        return str(e)


# ======================
# GRAFICO
# ======================

@app.route("/grafico")
def grafico():

    conn=get_conn()

    dados=
    conn.execute("""
    SELECT luz,data_hora
    FROM leituras
    ORDER BY id DESC
    LIMIT 20
    """).fetchall()

    conn.close()

    dados.reverse()

    return jsonify({

        "labels":[
            x[1][-8:]
            for x in dados
        ],

        "valores":[
            x[0]
            for x in dados
        ]

    })


# ======================
# START
# ======================

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
