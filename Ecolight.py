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
CIDADE = "Itajuba MG"


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

        ultima_data = datetime.strptime(
            horario,
            "%d/%m/%Y %H:%M:%S"
        )

        segundos = (
            datetime.now()
            -
            ultima_data
        ).seconds

        online = segundos < 20

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

.dot{{
width:18px;
height:18px;

background:#00c853;

border-radius:50%;

display:inline-block;

margin-right:10px;

animation:pulse 1.5s infinite;
}}

@keyframes pulse{{
50%{{opacity:.4}}
}}

.toast{{
position:fixed;

top:20px;

right:20px;

background:#1565c0;

color:white;

padding:18px;

border-radius:12px;

display:none;

z-index:999;
}}

</style>

</head>

<body>

<div class="toast" id="toast">

Atualizando...

</div>

<header>

<h1>

🌿 EcoLight Solutions

</h1>

<p>

Monitoramento Inteligente

</p>

</header>

<div class="cards">

<div class="card">

Sistema

<div
class="valor"

id="status">

Carregando...

</div>

</div>

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

🌤 Clima

<div
class="valor"
id="temp">

--

</div>

<div
id="clima">

Carregando...

</div>

</div>

<div class="card">

🔔 Notificação

<div
class="valor"

style="font-size:20px"

id="alerta">

Nenhuma

</div>

</div>

</div>

<div class="box">

<h2>

📈 Histórico da Luminosidade

</h2>

<canvas
id="grafico">

</canvas>

</div>

<script>

let chart;

function notificar(texto){{

let t=
document.getElementById(
"toast"
);

t.innerText=
texto;

t.style.display=
"block";

setTimeout(
()=>{{
t.style.display=
"none";
}},
2500
);

}}

async function atualizar(){

const r=
await fetch(
"/api/cards"
);

const d=
await r.json();

let status =
document.getElementById(
"status"
);

if(d.online){

status.innerHTML=
'<span class="dot"></span> Online';

status.style.color=
"#00c853";

}

else{

status.innerHTML=
'🔴 Offline';

status.style.color=
"#d50000";

}

luz.innerText=
d.luz;

consumo.innerText=
d.consumo+
" kWh";

economia.innerText=
d.economia+
"%";

}

const c=
await fetch(
"/api/clima"
);

const clima=
await c.json();

temp.innerText=
clima.temp+
"°C";

document
.getElementById(
"clima"
)
.innerText=

clima.descricao+

" • "+

clima.umidade+

"%";

if(
Number(clima.temp)>=35
){{
alerta.innerText=
"🔥 Calor alto";

notificar(
"Temperatura elevada"
);

}}

else if(
d.luz<300
){{
alerta.innerText=
"⚠ Ambiente escuro";

notificar(
"Baixa luminosidade"
);

}}

else{{

alerta.innerText=
"✓ Normal";

}}

const g=
await fetch(
"/grafico"
);

const dados=
await g.json();

if(!chart){{

chart=
new Chart(

document
.getElementById(
"grafico"
),

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

tension:.4,

borderWidth:3,

backgroundColor:
"rgba(21,101,192,.15)",

borderColor:
"#1565c0"

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
