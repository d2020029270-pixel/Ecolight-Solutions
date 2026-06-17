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
<!DOCTYPE html>

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
background:linear-gradient(135deg,#1565c0,#1e88e5);
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
box-shadow:0 10px 25px rgba(0,0,0,.08);
}}

.valor{{
font-size:32px;
font-weight:bold;
color:#1565c0;
}}

.online{{color:#00c853;}}
.offline{{color:#d50000;}}

.box{{
margin:25px;
padding:25px;
background:white;
border-radius:20px;
}}

.toast{{
position:fixed;
top:20px;
right:20px;
background:#1565c0;
color:white;
padding:15px;
border-radius:12px;
display:none;
}}

</style>

</head>

<body>

<div class="toast" id="toast"></div>

<header>

<h1>🌿 EcoLight Solutions</h1>

<p>Monitoramento Inteligente</p>

</header>

<div class="cards">

<div class="card">
Sistema
<div class="valor" id="status">
{"🟢 Online" if d["online"] else "🔴 Offline"}
</div>
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
<div class="valor" id="temp">--</div>
<div id="clima">
Carregando...
</div>
</div>

<div class="card">
🔔 Notificação
<div class="valor" id="alerta">
Normal
</div>
</div>

</div>

<div class="box">

<h2>📈 Histórico da Luminosidade</h2>

<canvas id="grafico"></canvas>

</div>

<script>

let chart;

function toast(txt){{
let t=document.getElementById("toast");

t.innerText=txt;

t.style.display="block";

setTimeout(()=>{{
t.style.display="none";
}},3000);

}}

async function atualizar(){{

let r=
await fetch("/api/cards");

let d=
await r.json();

document.getElementById(
"luz"
).innerText=d.luz;

document.getElementById(
"consumo"
).innerText=
d.consumo+" kWh";

document.getElementById(
"economia"
).innerText=
d.economia+"%";

document.getElementById(
"status"
).innerHTML=
d.online
?
"🟢 Online"
:
"🔴 Offline";


let climaReq=
await fetch(
"/api/clima"
);

let clima=
await climaReq.json();

temp.innerText=
clima.temp+"°C";

document.getElementById(
"clima"
).innerText=
clima.descricao+
" • "+
clima.umidade+
"%";

if(
clima.chuva==="Sim"
){{
alerta.innerText=
"☔ Chuva prevista";
}}

else if(
d.luz<300
){{
alerta.innerText=
"⚠ Baixa luz";
}}

else{{
alerta.innerText=
"✓ Normal";
}}


let g=
await fetch(
"/grafico"
);

let dados=
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
labels:dados.labels,

datasets:[{{
label:"LDR",

data:dados.valores,

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
