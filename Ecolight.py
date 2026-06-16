from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import os

EMPRESA = "EcoLight Solutions"
DB_NAME = "ecolight.db"

app = Flask(__name__)
@app.route("/")
def home():

    d = obter_dados()

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>{EMPRESA}</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

*{{
margin:0;
padding:0;
box-sizing:border-box;
font-family:Segoe UI;
}}

body{{
background:#eef3fb;
}}

header{{
background:linear-gradient(135deg,#1565c0,#1e88e5);
color:white;
padding:30px;
text-align:center;
}}

header h1{{
font-size:40px;
}}

header p{{
margin-top:10px;
opacity:.9;
}}

.menu{{
display:flex;
justify-content:center;
gap:40px;

background:white;

padding:15px;

box-shadow:0 2px 10px rgba(0,0,0,.08);
}}

.menu div{{
cursor:pointer;
font-weight:600;
}}

.cards{{
display:grid;

grid-template-columns:
repeat(auto-fit,minmax(240px,1fr));

gap:18px;

padding:25px;
}}

.card{{
background:white;

border-radius:20px;

padding:25px;

box-shadow:
0 10px 25px rgba(0,0,0,.08);

transition:.3s;
}}

.card:hover{{
transform:translateY(-6px);
}}

.titulo{{
font-size:15px;
color:#666;
}}

.valor{{
margin-top:10px;

font-size:34px;

font-weight:bold;

color:#1565c0;
}}

.status{{
display:flex;
align-items:center;
gap:10px;
}}

.dot{{
width:18px;
height:18px;

border-radius:50%;

background:#00c853;

box-shadow:
0 0 20px #00c853;

animation:pulse 1.4s infinite;
}}

@keyframes pulse{{
50%{{opacity:.5}}
}}

.box{{
margin:25px;

background:white;

border-radius:20px;

padding:25px;

box-shadow:
0 10px 25px rgba(0,0,0,.08);
}}

canvas{{
max-height:350px;
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
}}

</style>

</head>

<body>

<header>

<h1>🌿 EcoLight Solutions</h1>

<p>Monitoramento Inteligente de Energia</p>

</header>

<div class="menu">

<div>📊 Dashboard</div>

<div>🕒 Histórico</div>

<div>⚙ Configurações</div>

</div>

<div class="cards">

<div class="card">

<div class="titulo">

Sistema

</div>

<div class="valor status">

<div class="dot"></div>

Online

</div>

</div>

<div class="card">

<div class="titulo">

☀ Luminosidade

</div>

<div class="valor"
id="luz">

{d["luz"]}

</div>

</div>

<div class="card">

<div class="titulo">

⚡ Consumo

</div>

<div class="valor"
id="consumo">

{d["consumo"]}

kWh

</div>

</div>

<div class="card">

<div class="titulo">

🌱 Economia

</div>

<div class="valor"
id="economia">

{d["economia"]}%

</div>

</div>

<div class="card">

<div class="titulo">

🕒 Última atualização

</div>

<div class="valor"

style="font-size:22px"

id="hora">

{d["horario"]}

</div>

</div>

<div class="card">

<div class="titulo">

🔔 Alertas

</div>

<div class="valor"

style="font-size:22px"

id="alerta">

Nenhum

</div>

</div>

</div>

<div class="box">

<h2>

📈 Luminosidade em Tempo Real

</h2>

<br>

<canvas id="grafico"></canvas>

</div>

<div class="toast"
id="toast">
Novo dado recebido
</div>

<script>

let chart;

function aviso(txt){{
let t=
document.getElementById(
"toast"
);

t.innerText=
txt;

t.style.display=
"block";

setTimeout(
()=>{{
t.style.display=
"none";
}},
3000
);
}}

async function atualizar(){{

const cards=
await fetch(
"/api/cards"
);

const d=
await cards.json();

document
.getElementById("luz")
.innerText=
d.luz;

document
.getElementById("consumo")
.innerText=
d.consumo+
" kWh";

document
.getElementById("economia")
.innerText=
d.economia+
"%";

document
.getElementById("hora")
.innerText=
d.horario;

if(
d.luz<300
){{
document
.getElementById(
"alerta"
)
.innerText=
"Baixa luminosidade";
}}
else{{
document
.getElementById(
"alerta"
)
.innerText=
"Nenhum";
}}

const r=
await fetch(
"/grafico"
);

const dados=
await r.json();

if(!chart){{

chart=
new Chart(
document.getElementById(
"grafico"
),{{

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

tension:.5,

borderWidth:4,

backgroundColor:
"rgba(21,101,192,.18)",

borderColor:
"#1565c0",

pointRadius:0

}}]

}}

}});

}}

else{{

chart.data.labels=
dados.labels;

chart.data.datasets[0].data=
dados.valores;

chart.update();

}}

aviso(
"Dados atualizados"
);

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
