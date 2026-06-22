from flask import Flask, render_template_string, jsonify, request
import os
import time

app = Flask(__name__)

# Variável global para armazenar a última leitura do sensor e o tempo
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0
}

@app.route("/update")
def update():
    """Rota para o ESP8266 enviar dados de forma robusta"""
    # Recebe o valor como texto para podermos limpar qualquer caractere invisível
    luz_bruta = request.args.get("luz", "0")
    
    # Filtra apenas os números, eliminando aspas, espaços ou lixo de requisição HTTPS
    luz_limpa = ''.join(filter(str.isdigit, str(luz_bruta)))
    
    if luz_limpa:
        dados_sensor["luz"] = int(luz_limpa)
    else:
        dados_sensor["luz"] = 0
        
    dados_sensor["ultima_atualizacao"] = time.time()  # Registra o momento do envio
    return "OK"

@app.route("/api/get-luz")
def get_luz():
    """Rota para o frontend consultar o valor atual e o status"""
    agora = time.time()
    
    # Se a placa não mandar dados por mais de 7 segundos, assume que está Offline
    if agora - dados_sensor["ultima_atualizacao"] > 7:
        status = "Offline"
    else:
        status = "Online"
        
    return jsonify({
        "luz": dados_sensor["luz"],
        "status": status
    })

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EcoLight Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-slate-50 min-h-screen">
        <div class="max-w-4xl mx-auto p-6">
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-3xl font-bold text-slate-800">🌿 EcoLight Solutions</h1>
                <div id="status" class="px-4 py-1 rounded-full font-bold text-white transition-all duration-300">Verificando...</div>
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
                try {
                    const res = await fetch('/api/get-luz');
                    const data = await res.json();
                    
                    const luz = parseInt(data.luz);
                    const statusPlaca = data.status;
                    
                    const statusElemento = document.getElementById('status');
                    statusElemento.innerText = statusPlaca;
                    
                    if (statusPlaca === "Online") {
                        statusElemento.className = "px-4 py-1 rounded-full bg-green-500 text-white font-bold animate-pulse";
                        document.getElementById('valor-luz').innerText = luz;
                        
                        if(luz < 300) {
                            document.getElementById('alerta-box').classList.remove('hidden');
                        } else {
                            document.getElementById('alerta-box').classList.add('hidden');
                        }
                    } else {
                        statusElemento.className = "px-4 py-1 rounded-full bg-red-500 text-white font-bold";
                        document.getElementById('valor-luz').innerText = "Desconectado";
                        document.getElementById('alerta-box').classList.add('hidden');
                    }
                    
                    if (statusPlaca === "Online") {
                        const agora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        if(!chart) {
                            chart = new Chart(document.getElementById('grafico'), { 
                                type: 'line', 
                                data: { 
                                    labels: [agora], 
                                    datasets: [{
                                        label: 'LDR', 
                                        data: [luz], 
                                        borderColor: '#2563eb',
                                        tension: 0.2
                                    }] 
                                },
                                options: { responsive: true }
                            });
                        } else {
                            chart.data.labels.push(agora);
                            chart.data.datasets[0].data.push(luz);
                            if(chart.data.datasets[0].data.length > 15) {
                                chart.data.labels.shift();
                                chart.data.datasets[0].data.shift();
                            }
                            chart.update();
                        }
                    }
                } catch (error) {
                    console.error("Erro ao buscar dados:", error);
                    document.getElementById('status').className = "px-4 py-1 rounded-full bg-red-500 text-white font-bold";
                    document.getElementById('status').innerText = "Erro Servidor";
                }
            }
            setInterval(atualizar, 2000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    # Garante a porta dinâmica exigida pelo Render
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
