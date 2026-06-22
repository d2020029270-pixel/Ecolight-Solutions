from flask import Flask, render_template_string, jsonify, request
import os
import time

app = Flask(__name__)

# Dicionário global
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0,
    "consumo_acumulado": 0.0,
    "tempo_eco_acumulado": 0.0 # Conta o tempo de luz natural para o CO2
}

# Constantes de Engenharia
TARIFA_KWH = 0.95
POTENCIA_LAMPADAS_KW = 0.025 # 25W simulados
EMISSAO_CO2_POR_KWH_GRAMAS = 85.0 # Média genérica de gramas de CO2 por kWh

def recalcular_consumo(valor_luz):
    agora = time.time()
    if dados_sensor["ultima_atualizacao"] > 0:
        tempo_passado = agora - dados_sensor["ultima_atualizacao"]
        horas_passadas = tempo_passado / 3600.0
        
        if valor_luz < 300:
            # Escuro: Sistema artificial ligado (Gasta dinheiro e energia)
            dados_sensor["consumo_acumulado"] += POTENCIA_LAMPADAS_KW * horas_passadas
        else:
            # Claro: Sistema artificial desligado (Ganha horas ecológicas)
            dados_sensor["tempo_eco_acumulado"] += horas_passadas
            
    dados_sensor["ultima_atualizacao"] = agora

@app.route("/update")
def update():
    luz_bruta = request.args.get("luz", "0")
    luz_limpa = ''.join(filter(str.isdigit, str(luz_bruta)))
    valor_final = int(luz_limpa) if luz_limpa else 0
    
    recalcular_consumo(valor_final)
    dados_sensor["luz"] = valor_final
    return "OK"

@app.route("/api/get-luz")
def get_luz():
    agora = time.time()
    luz = dados_sensor["luz"]
    
    recalcular_consumo(luz)
    status = "Offline" if agora - dados_sensor["ultima_atualizacao"] > 7 else "Online"
        
    taxa_economia = round((luz / 1024.0) * 100)
    taxa_economia = max(0, min(100, taxa_economia))
    
    # Cálculos Físicos
    tensao_calculada = (luz / 1023.0) * 3.3
    tensao_calculada = max(0.0, min(3.3, tensao_calculada))
    
    # Estimativa de Iluminância em Lux (0 a ~1000 Lux)
    lux_estimado = int((luz / 1023.0) * 1000)
    
    # Cálculo Financeiro e Sustentabilidade
    custo_rs = dados_sensor["consumo_acumulado"] * TARIFA_KWH
    
    # Gramas de CO2 que deixaram de ir para a atmosfera
    co2_poupado = dados_sensor["tempo_eco_acumulado"] * POTENCIA_LAMPADAS_KW * EMISSAO_CO2_POR_KWH_GRAMAS
        
    return jsonify({
        "luz": luz,
        "status": status,
        "tensao": f"{tensao_calculada:.2f}",
        "lux": lux_estimado,
        "consumo": f'{dados_sensor["consumo_acumulado"]:.4f}', 
        "custo": f'{custo_rs:.2f}',
        "economia": taxa_economia,
        "co2": f"{co2_poupado:.2f}"
    })

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EcoLight Pro | Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-[#0a0a0a] min-h-screen flex flex-col text-slate-200">
        <div class="max-w-5xl mx-auto p-6 flex-grow w-full">
            
            <div class="flex items-center justify-between mb-8 border-b border-gray-800 pb-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(37,99,235,0.5)]">
                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    </div>
                    <div>
                        <h1 class="text-3xl font-bold text-white tracking-tight">EcoLight Solutions</h1>
                        <p class="text-sm text-blue-400 font-medium">Painel de Monitoramento Telemetria</p>
                    </div>
                </div>
                <div id="badge-modo" class="hidden md:flex px-4 py-2 rounded-full text-sm font-bold border transition-all duration-300">
                    --
                </div>
            </div>

            <div class="flex gap-3 mb-6">
                <button id="btn-painel" onclick="mostrar('painel')" class="px-5 py-2.5 bg-blue-600 text-white rounded-lg font-bold transition shadow-[0_0_10px_rgba(37,99,235,0.3)] text-sm">Painel Principal</button>
                <button id="btn-historico" onclick="mostrar('historico')" class="px-5 py-2.5 bg-gray-900 border border-gray-800 text-slate-400 rounded-lg font-bold hover:bg-gray-800 hover:text-white transition shadow-sm text-sm">Análise Histórica</button>
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                
                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-blue-500/50 transition-colors">
                    <div class="flex items-center justify-between mb-4">
                        <p class="text-slate-400 font-semibold text-sm">Leitura Óptica</p>
                        <div class="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20"><svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg></div>
                    </div>
                    <div>
                        <h2 class="text-4xl font-black text-white" id="valor-luz">--</h2>
                        <div class="flex gap-4 mt-2">
                            <p class="text-sm font-semibold text-blue-400" id="valor-tensao">0.00 V</p>
                            <p class="text-sm font-semibold text-amber-400" id="valor-lux">0 Lux</p>
                        </div>
                    </div>
                </div>

                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-cyan-500/50 transition-colors">
                    <div class="flex items-center justify-between mb-4">
                        <p class="text-slate-400 font-semibold text-sm">Consumo Acumulado</p>
                        <div class="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20"><svg class="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg></div>
                    </div>
                    <h2 class="text-3xl font-bold text-white" id="valor-consumo">0.0000 <span class="text-sm text-slate-500 font-medium">kWh</span></h2>
                </div>

                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-indigo-500/50 transition-colors">
                    <div class="flex items-center justify-between mb-4">
                        <p class="text-slate-400 font-semibold text-sm">Custo Estimado</p>
                        <div class="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20"><svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></div>
                    </div>
                    <h2 class="text-3xl font-bold text-indigo-400" id="valor-custo">R$ 0,00</h2>
                </div>

                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-teal-500/50 transition-colors">
                    <div class="flex items-center justify-between mb-2">
                        <p class="text-slate-400 font-semibold text-sm">Eficiência do Sistema</p>
                        <div class="p-2 bg-teal-500/10 rounded-lg border border-teal-500/20"><svg class="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg></div>
                    </div>
                    <div>
                        <h2 class="text-3xl font-black text-teal-400" id="valor-economia">--%</h2>
                        <div class="w-full bg-gray-800 rounded-full h-2 mt-2">
                            <div class="bg-teal-500 h-2 rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]" id="barra-economia" style="width: 0%"></div>
                        </div>
                        <div class="mt-3 flex justify-between items-center text-xs font-semibold text-slate-400 bg-gray-800/50 px-3 py-2 rounded-lg border border-gray-700/50">
                            <span>🌿 CO₂ Poupado:</span>
                            <span class="text-green-400" id="valor-co2">0.00 g</span>
                        </div>
                    </div>
                </div>

            </div>

            <div id="historico" class="hidden bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-800 mt-6">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-white">Gráfico de Leitura LDR (Estabilidade Fixa)</h3>
                    <span class="text-xs font-semibold text-blue-400 bg-blue-900/30 border border-blue-800/50 px-3 py-1 rounded-full">Janela de Metricas</span>
                </div>
                <div class="w-full h-64">
                    <canvas id="grafico"></canvas>
                </div>
            </div>
        </div>

        <footer class="border-t border-gray-800 py-6 mt-12 bg-[#0a0a0a] text-center text-sm text-slate-600">
            <p><strong class="text-slate-400">EcoLight Solutions</strong> &copy; 2024 - Todos os direitos reservados.</p>
            <p class="text-xs mt-1">Monitoramento Sustentável por ESP8266 & Flask.</p>
        </footer>

        <script>
            let chart;

            function mostrar(tab) {
                document.getElementById('painel').classList.add('hidden');
                document.getElementById('historico').classList.add('hidden');
                document.getElementById(tab).classList.remove('hidden');
                
                const btnActive = "px-5 py-2.5 bg-blue-600 text-white rounded-lg font-bold transition shadow-[0_0_10px_rgba(37,99,235,0.3)] text-sm";
                const btnInactive = "px-5 py-2.5 bg-gray-900 border border-gray-800 text-slate-400 rounded-lg font-bold hover:bg-gray-800 hover:text-white transition shadow-sm text-sm";

                if(tab === 'painel') {
                    document.getElementById('btn-painel').className = btnActive;
                    document.getElementById('btn-historico').className = btnInactive;
                } else {
                    document.getElementById('btn-historico').className = btnActive;
                    document.getElementById('btn-painel').className = btnInactive;
                }
            }

            async function atualizar() {
                try {
                    const res = await fetch('/api/get-luz');
                    const data = await res.json();
                    
                    if (data.status === "Online") {
                        document.getElementById('valor-luz').innerText = data.luz;
                        document.getElementById('valor-tensao').innerText = data.tensao + " V";
                        document.getElementById('valor-lux').innerText = data.lux + " Lux";
                        document.getElementById('valor-consumo').innerText = data.consumo + " kWh";
                        document.getElementById('valor-custo').innerText = "R$ " + data.custo.replace('.', ',');
                        
                        document.getElementById('valor-economia').innerText = data.economia + "%";
                        document.getElementById('barra-economia').style.width = data.economia + "%";
                        document.getElementById('valor-co2').innerText = data.co2.replace('.', ',') + " g";
                        
                        // Badge Dinâmico de Operação
                        const badge = document.getElementById('badge-modo');
                        if (data.luz >= 300) {
                            badge.className = "hidden md:flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold border border-green-500/50 bg-green-500/10 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.2)]";
                            badge.innerHTML = "☀️ Modo: Natural (Eco)";
                        } else {
                            badge.className = "hidden md:flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold border border-orange-500/50 bg-orange-500/10 text-orange-400 shadow-[0_0_10px_rgba(249,115,22,0.2)]";
                            badge.innerHTML = "💡 Modo: Artificial";
                        }
                        
                        // Configuração do Gráfico Dark Mode
                        Chart.defaults.color = '#94a3b8';
                        Chart.defaults.borderColor = '#334155';
                        
                        const agora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        if(!chart) {
                            chart = new Chart(document.getElementById('grafico'), { 
                                type: 'line', 
                                data: { labels: [agora], datasets: [{ label: 'Luminosidade', data: [data.luz], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.15)', fill: true, tension: 0.3, pointBackgroundColor: '#60a5fa' }] },
                                options: { 
                                    responsive: true, 
                                    maintainAspectRatio: false, 
                                    scales: { 
                                        y: { min: 0, max: 1024, grid: {color: '#1e293b'} }, 
                                        x: { grid: {color: '#1e293b'} } 
                                    } 
                                }
                            });
                        } else {
                            chart.data.labels.push(agora);
                            chart.data.datasets[0].data.push(data.luz);
                            
                            while (chart.data.labels.length > 10) {
                                chart.data.labels.shift();
                                chart.data.datasets[0].data.shift();
                            }
                            chart.update();
                        }
                    } else {
                        document.getElementById('valor-luz').innerText = "Offline";
                        document.getElementById('badge-modo').className = "hidden";
                    }
                } catch (error) {
                    console.error("Erro no fetch:", error);
                }
            }
            setInterval(atualizar, 2000);
            atualizar();
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
