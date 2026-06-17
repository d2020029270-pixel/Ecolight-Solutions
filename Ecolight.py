from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import os

# ==========================
# CONFIG
# ==========================

app = Flask(__name__)

EMPRESA = "EcoLight Solutions"
DB_NAME = "ecolight.db"


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
# SALVAR LEITURA
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
# DADOS DASHBOARD
# ==========================

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

            ultima_data = datetime.strptime(
                horario,
                "%d/%m/%Y %H:%M:%S"
            )

            online = (
                datetime.now()
                -
                ultima_data
            ).seconds < 15

        except:

            online = False

    else:

        luz = 0
        horario = "-"
        online = False

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
        "economia": economia,
        "online": online

    }


# ==========================
# API
# ==========================

@app.route("/api/cards")
def cards():

    return jsonify(
        obter_dados()
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
text-align:center;
background:linear-gradient(
135deg,
#1565c0,
#1e88e5
);
color:white;
}}

.cards{{
display:grid;

grid-template-columns:
repeat(
auto-fit,
minmax(240px,1fr)
);

gap:20px;
padding:25px;
}}

.card{{
background:white;

padding:25px;

border-radius:20px;

box-shadow:
0 10px 25px rgba(0,0,0,.08);
}}

.valor{{
font-size:32px;
font-weight:bold;
color:#1565c0;
}}

.box{{
margin:25px;

background:white;

padding:25px;

border-radius:20px;
}}

.status-box{{
display:flex;
align-items:center;
gap:10px;
}}

.dot{{
width:16px;
height:16px;
border-radius:50%;
}}

.online{{
background:#00c853;
}}

.offline{{
background:#d50000;
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

<div
class="valor status-box"
id="status">

</div>

</div>

<div class="card">

☀ Luminosidade

<div
class="valor"
id="luz">

{d["luz"]}

</div>

</div>

<div class="card">

⚡ Consumo

<div
class="valor"
id="consumo">

{d["consumo"]}

kWh

</div>

</div>

<div class="card">

🌱 Economia

<div
class="valor"
id="economia">

{d["economia"]}%

</div>

</div>

<div class="card">

🕒 Atualização

<div
class="valor"

style="font-size:20px"

id="hora">

{d["horario"]}

</div>

</div>

</div>

<div class="box">

<h2>

📈 Luminosidade

</h2>

<canvas id="grafico"></canvas>

</div>

<script>

let chart;

async function atualizar(){{

const r=
await fetch(
"/api/cards"
);

const d=
await r.json();

document
.getElementById(
"luz"
)
.innerText=
d.luz;

document
.getElementById(
"consumo"
)
.innerText=
d.consumo+
" kWh";

document
.getElementById(
"economia"
)
.innerText=
d.economia+
"%";

document
.getElementById(
"hora"
)
.innerText=
d.horario;


// STATUS

const status=
document.getElementById(
"status"
);

if(d.online){{

status.innerHTML=
`
<div class="dot online"></div>
Online
`;

}}

else{{

status.innerHTML=
`
<div class="dot offline"></div>
Offline
`;

}}


// GRAFICO

const g=
await fetch(
"/grafico"
);

const dados=
await g.json();

if(!chart){{

chart=
new Chart(
document.getElementById(
"grafico"
),
{{
type:"line",

data:{{
labels:
dados.labels,

datasets:[{{
label:
"LDR",

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
3000
);

</script>

</body>

</html>

"""


# ==========================
# RECEBER ESP
# ==========================

@app.route("/dados")
def receber():

    luz = request.args.get("luz")

    if luz is None:
        return "SEM DADOS"

    try:

        salvar_leitura(
            int(luz)
        )

        return "OK"

    except:

        return "ERRO"


# ==========================
# GRAFICO
# ==========================

@app.route("/grafico")
def grafico():

    conn = get_conn()

    c = conn.cursor()

    c.execute("""
    SELECT luz,data_hora
    FROM leituras
    ORDER BY id DESC
    LIMIT 20
    """)

    dados = c.fetchall()

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
