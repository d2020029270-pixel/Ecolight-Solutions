from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# Variável global para armazenar a última leitura do sensor
dados_sensor = {"luz": 0}

@app.route("/update")
def update():
    """Rota para o ESP8266 enviar dados"""
    luz = request.args.get("luz", 0)
    dados_sensor["luz"] = luz
    return "OK"

@app.route("/api/get-luz")
def get_luz():
    """Rota para o site consultar o valor"""
    return jsonify({"luz": dados_sensor["luz"]})

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>EcoLight Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-slate-50 min-h-screen">
        <div class="max-w-4xl mx-auto p-6">
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-3xl font-bold text-slate-800">🌿 EcoLight Solutions</h1>
                <div id="status" class="px-4 py-1 rounded-full bg-green-500 text-white font-bold animate-pulse">Online</div>
            </div>

            <div class="flex gap-4 mb-6">
                <button onclick="mostrar('painel')" class="px-6 py-2 bg-blue-600 text-white rounded-lg font-bold">Painel</button>
                <button onclick="mostrar('historico')" class="px-6 py-2 bg-slate-200 text-slate-600 rounded-lg font-bold hover:bg-slate-300">Histórico</button>
            </div>

            <div id="alerta-box" class="bg-orange-100 border-l-4 border-orange-500 text-orange-700 p-4 mb-6 hidden">
                <strong>Atenção:</strong> Pouca energia, economize!
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <p class="text-slate-500">Luminosidade (LDR)</p>
                    <h2 class="text-5xl font-black text-blue-600" id="valor-luz">--</h2>
                </div>
            </div>

            <div id="historico" class="hidden bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                <canvas id="grafico"></canvas>
            </div>
        </div>

        <script>
            let chart;
            function mostrar(tab) {
                document.getElementById('painel').classList.add('hidden');
                document.getElementById('historico').classList.add('hidden');
                document.getElementById(tab).classList.remove('hidden');
            }

            async function atualizar() {
                const res = await fetch('/api/get-luz');
                const data = await res.json();
                const luz = parseInt(data.luz);
                
                document.getElementById('valor-luz').innerText = luz;
                
                if(luz < 300) document.getElementById('alerta-box').classList.remove('hidden');
                else document.getElementById('alerta-box').classList.add('hidden');

                if(!chart) {
                    chart = new Chart(document.getElementById('grafico'), { 
                        type: 'line', 
                        data: { labels: ['Atual'], datasets: [{label: 'LDR', data: [luz], borderColor: '#2563eb'}] } 
                    });
                } else {
                    chart.data.datasets[0].data.push(luz);
                    if(chart.data.datasets[0].data.length > 10) chart.data.datasets[0].data.shift();
                    chart.update();
                }
            }
            setInterval(atualizar, 2000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
