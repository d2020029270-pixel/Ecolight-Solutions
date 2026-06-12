from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

EMPRESA = "EcoLight Solutions"
DB_NAME = "ecolight.db"

# =====================================
# CONEXÃO
# =====================================
def get_conn():
    return sqlite3.connect(DB_NAME)

# =====================================
# BANCO
# =====================================
def criar_banco():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leituras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        luz INTEGER NOT NULL,
        data_hora TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

criar_banco()

# =====================================
# SALVAR
# =====================================
def salvar_leitura(luz):
    criar_banco()
    conn = get_conn()
    cursor = conn.cursor()
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute(
        "INSERT INTO leituras (luz, data_hora) VALUES (?, ?)",
        (luz, data_hora)
    )
    conn.commit()
    conn.close()

# =====================================
# DASHBOARD DADOS
# =====================================
def obter_dados():
    criar_banco()
    conn = get_conn()
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
        luz, horario = ultima
    else:
        luz, horario = 0, "-"
        
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

# =====================================
# DADOS DOS CARDS (JSON PARA O FRONTEND)
# =====================================
@app.route("/api/cards")
def api_cards():
    d = obter_dados()
    return jsonify(d)

# =====================================
# HOME (DASHBOARD)
# =====================================
@app.route("/")
def home():
    d = obter_dados()
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{EMPRESA}</title>

<style>
body {{
    font-family: Arial;
    margin: 0;
    background: #f5f7fa;
}}
header {{
    background: #1565c0;
    color: white;
    text-align: center;
    padding: 25px;
}}
.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(220px,1fr));
    gap: 15px;
    padding: 20px;
}}
.card {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
}}
.valor {{
    font-size: 28px;
    font-weight: bold;
    color: #1565c0;
}}
.grafico {{
    margin: 20px;
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15);
}}
</style>
</head>

<body>

<header>
    <h1>🌿 EcoLight Solutions</h1>
    <p>Monitoramento Inteligente de Energia</p>
</header>

<div class="cards">
    <div class="card">
        <h3>📊 Leituras</h3>
        <div class="valor" id="card-leituras">{d['total']}</div>
    </div>
    <div class="card">
        <h3>☀️ Luminosidade</h3>
        <div class="valor" id="card-luz">{d['luz']}</div>
    </div>
    <div class="card">
        <h3>💡 Status</h3>
        <div class="valor" id="card-status">{d['status']}</div>
    </div>
    <div class="card">
        <h3>⚡ Consumo</h3>
        <div class="valor" id="card-consumo">{d['consumo']} kWh</div>
    </div>
    <div class="card">
        <h3>💰 Custo</h3>
        <div class="valor" id="card-custo">R$ {d['custo']}</div>
    </div>
    <div class="card">
        <h3>🌱 Economia</h3>
        <div class="valor" id="card-economia">{d['economia']}%</div>
    </div>
</div>

<div class="grafico">
    <h2>📈 Luminosidade</h2>
    <canvas id="grafico"></canvas>
</div>

<div class="grafico">
    <h2>💰 Gastos por Hora</h2>
    <canvas id="graficoGastos"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
let chart;
let chartGastos;

async function atualizar() {{
    // 1. Atualizar Cards
    try {{
        const rCards = await fetch('/api/cards');
        const dadosCards = await rCards.json();
        
        document.getElementById("card-leituras").innerText = dadosCards.total;
        document.getElementById("card-luz").innerText = dadosCards.luz;
        document.getElementById("card-status").innerText = dadosCards.status;
        document.getElementById("card-consumo").innerText = dadosCards.consumo + " kWh";
        document.getElementById("card-custo").innerText = "R$ " + dadosCards.custo;
        document.getElementById("card-economia").innerText = dadosCards.economia + "%";
    }} catch (e) {{
        console.error("Erro ao atualizar os cards:", e);
    }}

    // 2. Atualizar Grafico Luminosidade
    const r1 = await fetch('/grafico');
    const dados1 = await r1.json();

    if (!chart) {{
        chart = new Chart(document.getElementById('grafico'), {{
            type: 'line',
            data: {{
                labels: dados1.labels,
                datasets: [{{
                    label: 'Luminosidade',
                    data: dados1.valores,
                    borderColor: '#1565c0',
                    backgroundColor: 'rgba(21,101,192,0.2)',
                    fill: true,
                    tension: 0.4
                }}]
            }}
        }});
    }} else {{
        chart.data.labels = dados1.labels;
        chart.data.datasets[0].data = dados1.valores;
        chart.update();
    }}

    // 3. Atualizar Grafico Gastos
    const r2 = await fetch('/grafico_gastos');
    const dados2 = await r2.json();

    if (!chartGastos) {{
        chartGastos = new Chart(document.getElementById('graficoGastos'), {{
            type: 'bar',
            data: {{
                labels: dados2.labels,
                datasets: [{{
                    label: 'Gastos (R$)',
                    data: dados2.valores,
                    backgroundColor: '#f57c00'
                }}]
            }}
        }});
    }} else {{
        chartGastos.data.labels = dados2.labels;
        chartGastos.data.datasets[0].data = dados2.valores;
        chartGastos.update();
    }}
}}

atualizar();
setInterval(atualizar, 5000);
</script>

</body>
</html>
"""

# =====================================
# RECEBER DADOS DO ESP8266
# =====================================
@app.route("/dados")
def receber():
    luz = request.args.get("luz")
    if luz is None:
        return "SEM DADOS"
    try:
        salvar_leitura(int(luz))
        return "OK"
    except Exception as e:
        return f"ERRO: {e}"

# =====================================
# HISTÓRICO
# =====================================
@app.route("/historico")
def historico():
    criar_banco()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM leituras
        ORDER BY id DESC
        LIMIT 100
    """)
    registros = cursor.fetchall()
    conn.close()
    return jsonify([
        {"id": r[0], "luz": r[1], "data_hora": r[2]}
        for r in registros
    ])

# =====================================
# GRAFICO LUZ
# =====================================
@app.route("/grafico")
def grafico():
    criar_banco()
    conn = get_conn()
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
    return jsonify({
        "labels": [r[1][-8:] for r in registros],
        "valores": [r[0] for r in registros]
    })

# =====================================
# GRAFICO GASTOS POR HORA
# =====================================
@app.route("/grafico_gastos")
def grafico_gastos():
    criar_banco()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT luz, data_hora
        FROM leituras
        ORDER BY id DESC
        LIMIT 100
    """)
    registros = cursor.fetchall()
    conn.close()
    registros.reverse()
    
    labels = []
    valores = []
    for r in registros:
        hora = r[1][-8:-3]
        luz = r[0]
        custo = round((luz * 0.00045) * 0.95, 4)
        labels.append(hora)
        valores.append(custo)
        
    return jsonify({
        "labels": labels,
        "valores": valores
    })

# =====================================
# START
# =====================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
