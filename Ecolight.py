from flask import Flask, render_template_string, jsonify, request
import os
import time

app = Flask(__name__)

# Dicionário global gerenciando dados do sensor, tempo e métricas elétricas
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0,
    "consumo_acumulado": 0.0
}

def recalcular_consumo(valor_luz):
    """Calcula dinamicamente os kWh baseado no tempo de lâmpadas ligadas na maquete"""
    agora = time.time()
    if dados_sensor["ultima_atualizacao"] > 0:
        tempo_passado = agora - dados_sensor["ultima_atualizacao"]  # em segundos
        
        # Lógica: Se o LDR estiver abaixo de 300, as luzes da maquete acendem (consomem energia)
        # Simulando uma carga de iluminamento artificial de 25W (0.025 kW)
        if valor_luz < 300:
            horas = tempo_passado / 3600.0
            dados_sensor["consumo_acumulado"] += 0.025 * horas
            
    dados_sensor["ultima_atualizacao"] = agora

@app.route("/update")
def update():
    """Rota para o ESP8266 enviar dados de forma robusta"""
    luz_bruta = request.args.get("luz", "0")
    luz_limpa = ''.join(filter(str.isdigit, str(luz_bruta)))
    
    valor_final = int(luz_limpa) if luz_limpa else 0
    
    # Roda as regras de cálculo matemático de gastos antes de atualizar o valor fixo
    recalcular_consumo(valor_final)
    dados_sensor["luz"] = valor_final
    
    return "OK"

@app.route("/api/get-luz")
def get_luz():
    """Rota para o frontend consultar o valor atual, status e métricas calculadas"""
    agora = time.time()
    luz = dados_sensor["luz"]
    
    # Atualiza o cálculo do consumo até o exato segundo atual
    recalcular_consumo(luz)
    
    if agora - dados_sensor["ultima_atualizacao"] > 7:
        status = "Offline"
    else:
        status = "Online"
        
    # Cálculo de Economia Verde Dinâmica (0% a 100% proporcional à luz do sol)
    taxa_economia = round((luz / 1024.0) * 100)
    taxa_economia = max(0, min(100, taxa_economia))
    
    # Lógica de Clima Regional acoplada à luminosidade
    temp = 25 if luz > 400 else 18
    umid = 50 if luz > 400 else 80
    desc = "Ensolarado" if luz > 500 else "Nublado / Noite"
    clima_string = f"{temp}°C - {desc} ({umid}% Umid.)"
        
    return jsonify({
        "luz": luz,
        "status": status,
        "consumo": round(dados_sensor["consumo_acumulado"], 5),
        "economia": taxa_economia,
        "clima": clima_string
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
                <button id="btn-painel" onclick="mostrar('painel')" class="px-6 py-2 bg-blue-600 text-white rounded-lg font-bold transition">Painel</button>
                <button id="btn-historico" onclick="mostrar('historico')" class="px-6 py-2 bg-slate-200 text-slate-600 rounded-lg font-bold hover:bg-slate-300 transition">Histórico</button>
            </div>

            <div id="alerta-box" class="bg-orange-100 border-l-4 border-orange-500 text-orange-700 p-4 mb-6 hidden rounded-r-lg">
                <strong>Atenção:</strong> Pouca energia natural, economize! Sistema artificial ativado.
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <p class="text-slate-500 font-medium">Luminosidade (LDR)</p>
                    <h2 class="text-5xl font-black text-blue-600 mt-2" id="valor-luz">--</h2>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <p class="text-slate-500 font-medium">Clima Regional Estipulado</p>
                    <h2 class="text-2xl font-bold text-slate-800 mt-4" id="valor-clima">Carregando...</h2>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <p class="text-slate-500 font-medium">Consumo da Maquete</p>
                    <h2 class="text-3xl font-bold text-red-600 mt-3" id="valor-consumo">0.00000 kWh</h2>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <p class="text-slate-500 font-medium">Eficiência / Economia</p>
                    <h2 class="text-3xl font-bold text-green-600 mt-3" id="valor-economia">--%</h2>
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
                
                if(tab === 'painel') {
                    document.getElementById('btn-painel').className = "px-6 py-2 bg-blue-600 text-white rounded-lg font-bold transition";
                    document.getElementById('btn-historico').className = "px-6 py-2 bg-slate-200 text-slate-600 rounded-lg font-bold hover:bg-slate-300 transition";
                } else {
                    document.getElementById('btn-historico').className = "px-6 py-2 bg-blue-600 text-white rounded-lg font-bold transition";
                    document.getElementById('btn-painel').className = "px-6 py-2 bg-slate-200 text-slate-600 rounded-lg font-bold hover:bg-slate-300 transition";
                }
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
                        
                        // injeta as novas variáveis calculadas no back-end direto nos IDs corretos
                        document.getElementById('valor-luz').innerText = luz;
                        document.getElementById('valor-clima').innerText = data.clima;
                        document.getElementById('valor-consumo').innerText = data.consumo + " kWh";
                        document.getElementById('valor-economia').innerText = data.economia + "%";
                        
                        if(luz < 300) {
                            document.getElementById('alerta-box').classList.remove('hidden');
                        } else {
                            document.getElementById('alerta-box').classList.add('hidden');
                        }
                    } else {
                        statusElemento.className = "px-4 py-1 rounded-full bg-red-500 text-white font-bold";
                        document.getElementById('valor-luz').innerText = "Desconectado";
                        document.getElementById('valor-clima').innerText = "Sem Dados";
                        document.getElementById('valor-economia').innerText = "0%";
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
                                        label: 'Luminosidade', 
                                        data: [luz], 
                                        borderColor: '#2563eb',
                                        backgroundColor: 'rgba(37, 99, 235, 0.05)',
                                        fill: true,
                                        tension: 0.2
                                    }] 
                                },
                                options: { responsive: true, scales: { y: { min: 0, max: 1024 } } }
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
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
