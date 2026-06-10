from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)

EMPRESA = "EcoLight Solutions"

# =========================
# BANCO DE DADOS
# =========================

def criar_banco():
    conn = sqlite3.connect("ecolight.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leituras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        luz INTEGER,
        data_hora TEXT
    )
    """)

    conn.commit()
    conn.close()


def salvar_leitura(luz):
    conn = sqlite3.connect("ecolight.db")
    cursor = conn.cursor()

    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    cursor.execute(
        "INSERT INTO leituras (luz, data_hora) VALUES (?, ?)",
        (luz, data_hora)
    )

    conn.commit()
    conn.close()


def obter_dados():
    conn = sqlite3.connect("ecolight.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leituras")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT luz, data_hora
    FROM leituras
    ORDER BY id DESC
    LIMIT 1
    """)

    ultima = cursor.fetchone()

    conn.close()

    if ultima:
        luz = ultima[0]
        horario = ultima[1]
    else:
        luz = 0
        horario = "-"

    status = "💡 Ligada" if luz > 600 else "🌙 Desligada"

    consumo = round(total * 0.00045, 3)
    custo = round(consumo * 0.95, 2)
    economia = max(0, min(100, round((1000 - luz) / 10)))

    return {
        "total": total,
        "luz": luz,
        "horario": horario,
        "status": status,
        "consumo": consumo,
        "custo": custo,
        "economia": economia
    }


# =========================
# DASHBOARD
# =========================

@app.route("/")
def home():

    d = obter_dados()

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>EcoLight Solutions</title>

<style>

body {{
    font-family: Arial;
    margin: 0;
    background: #f5f5f5;
}}

.header {{
    background: #1565c0;
    color: white;
    text-align: center;
    padding: 25px;
}}

.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(250px,1fr));
    gap: 15px;
    padding: 20px;
}}

.card {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}}

.valor {{
    font-size: 28px;
    font-weight: bold;
    color: #1565c0;
}}

.grafico {{
    background: white;
    margin: 20px;
    padding: 20px;
    border-radius: 12px;
}}

</style>

</head>

<body>

<div class="header">
<h1>🌿 EcoLight Solutions</h1>
<p>Monitoramento Inteligente de Energia</p>
</div>

<div class="cards">

<div class="card">
<h3>📊 Leituras</h3>
<div class="valor">{d['total']}</div>
</div>

<div class="card">
<h3>☀️ Luminosidade</h3>
<div class="valor">{d['luz']}</div>
</div>

<div class="card">
<h3>💡 Status</h3>
<div class="valor">{d['status']}</div>
</div>

<div class="card">
<h3>⚡ Consumo</h3>
<div class="valor">{d['consumo']} kWh</div>
</div>

<div class="card">
<h3>💰 Custo</h3>
<div class="valor">R$ {d['custo']}</div>
</div>

<div class="card">
<h3>🌱 Economia</h3>
<div class="valor">{d['economia']}%</div>
</div>

</div>

<div class="grafico">
<h2>📈 Últimas Leituras</h2>
<canvas id="grafico"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>

let chart;

async function atualizar() {{

    const r = await fetch('/grafico');
    const dados = await r.json();

    if(!chart) {{

        chart = new Chart(
            document.getElementById('grafico'),
            {{
                type: 'line',
                data: {{
                    labels: dados.labels,
                    datasets: [{{
                        label: 'Luminosidade',
                        data: dados.valores
                    }}]
                }}
            }}
        );

    }} else {{

        chart.data.labels = dados.labels;
        chart.data.datasets[0].data = dados.valores;
        chart.update();
    }}
}}

atualizar();
setInterval(atualizar, 5000);

</script>

</body>
</html>
"""


# =========================
# RECEBER ESP8266
# =========================

@app.route("/dados")
def receber():

    luz = request.args.get("luz")

    if luz:

        try:
            salvar_leitura(int(luz))
            return "OK"
        except:
            return "ERRO"

    return "SEM DADOS"


# =========================
# HISTÓRICO
# =========================

@app.route("/historico")
def historico():

    conn = sqlite3.connect("ecolight.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM leituras
    ORDER BY id DESC
    LIMIT 100
    """)

    registros = cursor.fetchall()

    conn.close()

    lista = []

    for r in registros:
        lista.append({
            "id": r[0],
            "luz": r[1],
            "data_hora": r[2]
        })

    return jsonify(lista)


# =========================
# DADOS DO GRÁFICO
# =========================

@app.route("/grafico")
def grafico():

    conn = sqlite3.connect("ecolight.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT luz, data_hora
    FROM leituras
    ORDER BY id DESC
    LIMIT 20
    """)

    registros = cursor.fetchall()

    conn.close()

    registros.reverse()

    labels = []
    valores = []

    for r in registros:
        labels.append(r[1][-8:])
        valores.append(r[0])

    return jsonify({
        "labels": labels,
        "valores": valores
    })


# =========================
# INICIAR
# =========================

if __name__ == "__main__":

    criar_banco()

    print("=" * 40)
    print("ECOLIGHT SOLUTIONS")
    print("Servidor iniciado")
    print("=" * 40)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
