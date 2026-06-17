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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
# DADOS
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

        segundos = (
            datetime.now()
            -
            datetime.strptime(
                horario,
                "%d/%m/%Y %H:%M:%S"
            )
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


# ======================
# CLIMA
# ======================

def obter_clima():

    try:

        r = requests.get(
            f"https://wttr.in/{CIDADE}?format=j1",
            timeout=5
        )

        atual = (
            r.json()
            ["current_condition"][0]
        )

        return {

            "temp":
            atual["temp_C"],

            "umidade":
            atual["humidity"],

            "descricao":
            atual["weatherDesc"][0]["value"]

        }

    except:

        return {

            "temp":"--",

            "umidade":"--",

            "descricao":"Indisponível"

        }


# ======================
# API
# ======================

@app.route("/api/cards")
def api_cards():

    return jsonify(
        obter_dados()
    )


@app.route("/api/clima")
def api_clima():

    return jsonify(
        obter_clima()
    )


@app.route("/dados")
def dados():

    luz = request.args.get(
        "luz"
    )

    if not luz:

        return "SEM DADOS"

    salvar_leitura(
        int(luz)
    )

    return "OK"


@app.route("/grafico")
def grafico():

    conn = get_conn()

    dados = conn.execute("""
    SELECT luz,data_hora
    FROM leituras
    ORDER BY id DESC
    LIMIT 20
    """).fetchall()

    conn.close()

    dados.reverse()

    return jsonify({

        "labels":
        [
            x[1][-8:]
            for x in dados
        ],

        "valores":
        [
            x[0]
            for x in dados
        ]

    })


# ======================
# HOME
# ======================

@app.route("/")
def home():

    return """
<html>

<head>

<title>EcoLight Solutions</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body{
margin:0;
font-family:Arial;
background:#eef3fb;
}

header{
padding:30px;
background:#1565c0;
color:white;
text-align:center;
}

.cards{
display:grid;
grid-template-columns:
repeat(auto-fit,minmax(250px,1fr));
gap:20px;
padding:25px;
}

.card{
background:white;
padding:20px;
border-radius:20px;
}

.valor{
font-size:32px;
color:#1565c0;
}

.online{
color:#00c853;
}

.offline{
color:red;
}

</style>

</head>

<body>

<header>

<h1>
🌿 EcoLight
</h1>

</header>

<div class="cards">

<div class="card">

Sistema

<div
id="status"
class="valor">

Carregando

</div>

</div>

<div class="card">

Luminosidade

<div
id="luz"
class="valor">

--

</div>

</div>

<div class="card">

Clima

<div
id="temp"
class="valor">

--

</div>

<div id="clima">

--

</div>

</div>

<div class="card">

Alerta

<div
id="alerta"
class="valor">

--

</div>

</div>

</div>

<div class="card">

<canvas
id="grafico">

</canvas>

</div>

<script>

let chart;

async function atualizar(){

let d=
await (
await fetch(
"/api/cards"
)
).json();

status.innerHTML=
d.online
?
"🟢 Online"
:
"🔴 Offline";

luz.innerText=
d.luz;

let c=
await(
await fetch(
"/api/clima"
)
).json();

temp.innerText=
c.temp+"°C";

clima.innerText=
c.descricao;

alerta.innerText=

d.luz<300
?
"⚠ Pouca Luz"
:
"✓ Normal";

let g=
await(
await fetch(
"/grafico"
)
).json();

if(!chart){

chart=
new Chart(
grafico,
{
type:"line",

data:{

labels:
g.labels,

datasets:[{

data:
g.valores,

fill:true

}]

}

}
);

}

else{

chart.data.labels=
g.labels;

chart.data.datasets[0].data=
g.valores;

chart.update();

}

}

atualizar();

setInterval(
atualizar,
3000
);

</script>

</body>

</html>
"""


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
