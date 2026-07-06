from flask import Flask, render_template_string, jsonify, request
import os
import time

app = Flask(__name__)

# Dicionário global com o banco de baterias virtual
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0,
    "energia_gerada_kwh": 0.0,
    "tempo_eco_acumulado": 0.0,
    "tempo_total_rodando": 0.0,
    "bateria_porcentagem": 0.0, # Estado de carga da bateria (0 a 100%)
    "status_rele": 0            # 0 = Desligado, 1 = Ligado (Descarte de energia)
}

# Constantes de Engenharia
TARIFA_KWH = 0.95
POTENCIA_MAX_W = 500.0 
EMISSAO_CO2_POR_KWH_GRAMAS = 85.0
CAPACIDADE_BATERIA_KWH = 0.05 # Tamanho do banco de baterias simulado

def recalcular_energia(valor_luz):
    agora = time.time()
    if dados_sensor["ultima_atualizacao"] > 0:
        tempo_passado = agora - dados_sensor["ultima_atualizacao"]
        horas_passadas = tempo_passado / 3600.0
        
        dados_sensor["tempo_total_rodando"] += horas_passadas
        
        # Geração atual
        potencia_atual_w = (valor_luz / 1023.0) * POTENCIA_MAX_W
        potencia_atual_kw = potencia_atual_w / 1000.0
        
        # Acumula energia total
        dados_sensor["energia_gerada_kwh"] += potencia_atual_kw * horas_passadas
        
        # --- LÓGICA DA BATERIA VIRTUAL E AUTOMAÇÃO ---
        # Multiplicador ajustado para 100 (aprox. 5 a 6 minutos para carga completa sob luz forte)
        if dados_sensor["status_rele"] == 0:
            dados_sensor["bateria_porcentagem"] += (potencia_atual_kw * horas_passadas * 100) / CAPACIDADE_BATERIA_KWH
            if dados_sensor["bateria_porcentagem"] >= 100.0:
                dados_sensor["bateria_porcentagem"] = 100.0
                dados_sensor["status_rele"] = 1 # Bateria cheia! Ativa o descarte
        else:
            # Se o relé está LIGADO, o aparelho consome energia e descarrega um pouco a bateria
            consumo_aparelho_kw = 0.250 # Aparelho simulado consome 250W
            saldo_energia = potencia_atual_kw - consumo_aparelho_kw
            dados_sensor["bateria_porcentagem"] += (saldo_energia * horas_passadas * 100) / CAPACIDADE_BATERIA_KWH
            
            # Limite de segurança para desligar o relé
            if dados_sensor["bateria_porcentagem"] <= 75.0:
                dados_sensor["status_rele"] = 0
                
        # === TRAVA DE LIMITES FÍSICOS ===
        if dados_sensor["bateria_porcentagem"] > 100.0:
            dados_sensor["bateria_porcentagem"] = 100.0
        elif dados_sensor["bateria_porcentagem"] < 0.0:
            dados_sensor["bateria_porcentagem"] = 0.0
            
        if valor_luz >= 300:
            dados_sensor["tempo_eco_acumulado"] += horas_passadas
            
    dados_sensor["ultima_atualizacao"] = agora

@app.route("/update")
def update():
    luz_bruta = request.args.get("luz", "0")
    luz_limpa = ''.join(filter(str.isdigit, str(luz_bruta)))
    valor_final = int(luz_limpa) if luz_limpa else 0
    
    recalcular_energia(valor_final)
    dados_sensor["luz"] = valor_final
    
    return f"RELE:{dados_sensor['status_rele']}"

@app.route("/api/get-luz")
def get_luz():
    agora = time.time()
    luz = dados_sensor["luz"]
    
    recalcular_energia(luz)
    status = "Offline" if agora - dados_sensor["ultima_atualizacao"] > 7 else "Online"
        
    taxa_eficiencia = round((luz / 1024.0) * 100)
    taxa_eficiencia = max(0, min(100, taxa_eficiencia))
    
    tensao_calculada = (luz / 1023.0) * 3.3
    lux_estimado = int((luz / 1023.0) * 1000)
    potencia_w = (luz / 1023.0) * POTENCIA_MAX_W
    
    energia_acumulada = dados_sensor["energia_gerada_kwh"]
    economia_rs = energia_acumulada * TARIFA_KWH
    co2_poupado = energia_acumulada * EMISSAO_CO2_POR_KWH_GRAMAS
    
    tempo_decorrido = dados_sensor["tempo_total_rodando"]
    if tempo_decorrido > 0.0001:
        fator_mensal = 720.0 / tempo_decorrido
        proj_energia_mes = energia_acumulada * fator_mensal
    else:
        proj_energia_mes = (potencia_w / 1000.0) * 5.0 * 30.0
        
    proj_economia_mes = proj_energia_mes * TARIFA_KWH
    proj_co2_mes = proj_energia_mes * EMISSAO_CO2_POR_KWH_GRAMAS
        
    return jsonify({
        "luz": luz,
        "status": status,
        "tensao": f"{tensao_calculada:.2f}",
        "lux": lux_estimado,
        "potencia_w": f"{potencia_w:.1f}",
        "energia_kwh": f'{energia_acumulada:.6f}', 
        "economia_rs": f'{economia_rs:.4f}',
        "eficiencia": taxa_eficiencia,
        "co2": f"{co2_poupado:.2f}",
        "proj_energia": f"{proj_energia_mes:.2f}",
        "proj_economia": f"{proj_economia_mes:.2f}",
        "proj_co2": f"{proj_co2_mes:.1f}",
        "bateria": f"{dados_sensor['bateria_porcentagem']:.1f}",
        "status_rele": dados_sensor["status_rele"]
    })

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EcoLight Pro | Dashboard Fotovoltaico</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-[#0a0a0a] min-h-screen flex flex-col text-slate-200">
        <div class="max-w-6xl mx-auto p-6 flex-grow w-full">
            
            <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-8 border-b border-gray-800 pb-4 gap-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(37,99,235,0.5)]">
                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    </div>
                    <div>
                        <h1 class="text-3xl font-bold text-white tracking-tight">EcoLight Solar</h1>
                        <p class="text-sm text-blue-400 font-medium">Telemetria e Controle de Carga IoT</p>
                    </div>
                </div>
                
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-3 px-4 py-2 rounded-xl bg-gray-900 border border-gray-800 shadow-sm min-w-[180px]">
                        <span id="weather-icon" class="text-2xl drop-shadow-md">⛅</span>
                        <div>
                            <p class="text-xs text-slate-400 font-semibold tracking-wide">ITAJUBÁ, MG</p>
                            <p class="text-sm font-bold text-white"><span id="weather-temp">-- °C</span> <span class="text-xs text-slate-500 font-normal ml-1" id="weather-desc">Buscando...</span></p>
                        </div>
                    </div>
                    <div id="badge-modo" class="hidden md:flex px-4 py-2.5 rounded-xl text-sm font-bold border transition-all duration-300">--</div>
                </div>
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
                
                <div class="bg-gray-900 p-4 rounded-2xl border border-gray-800 flex flex-col justify-between">
                    <p class="text-slate-400 font-semibold text-xs">Leitura Óptica</p>
                    <h2 class="text-3xl font-black text-white mt-2" id="valor-luz">--</h2>
                    <div class="flex gap-2 mt-1">
                        <p class="text-xs font-semibold text-blue-400" id="valor-tensao">0.00 V</p>
                        <p class="text-xs font-semibold text-amber-400" id="valor-lux">0 Lux</p>
                    </div>
                </div>

                <div class="bg-gray-900 p-4 rounded-2xl border border-gray-800 flex flex-col justify-between">
                    <p class="text-slate-400 font-semibold text-xs">Geração Solar</p>
                    <h2 class="text-3xl font-bold text-white mt-2" id="valor-potencia">0.0 W</h2>
                    <p class="text-[10px] font-semibold text-cyan-400 mt-1" id="valor-energia-kwh">Total: 0.00 kWh</p>
                </div>

                <div class="bg-gray-900 p-4 rounded-2xl border border-gray-800 flex flex-col justify-between hover:border-amber-500/40 transition-colors">
                    <div class="flex justify-between items-center">
                        <p class="text-slate-400 font-semibold text-xs">Banco de Baterias</p>
                        <span id="bateria-icon" class="text-sm">🔋</span>
                    </div>
                    <h2 class="text-3xl font-bold text-amber-400 mt-2" id="valor-bateria">0.0%</h2>
                    <div class="w-full bg-gray-800 h-1.5 rounded-full mt-1 overflow-hidden">
                        <div id="barra-bateria" class="bg-amber-500 h-full transition-all duration-300" style="width: 0%"></div>
                    </div>
                </div>

                <div class="bg-gray-900 p-4 rounded-2xl border border-gray-800 flex flex-col justify-between" id="card-rele">
                    <p class="text-slate-400 font-semibold text-xs">Carga Excedente (Relé)</p>
                    <h2 class="text-xl font-bold text-slate-400 mt-2" id="status-rele-texto">DESLIGADO</h2>
                    <p class="text-[10px] text-slate-500 mt-1" id="status-rele-desc">Aguardando Sobra</p>
                </div>

                <div class="bg-gray-900 p-4 rounded-2xl border border-gray-800 flex flex-col justify-between">
                    <p class="text-slate-400 font-semibold text-xs">Economia Total</p>
                    <h2 class="text-2xl font-bold text-indigo-400 mt-2" id="valor-economia-rs">R$ 0,00</h2>
                    <p class="text-[10px] text-green-400 mt-1">🌿 CO₂: <span id="valor-co2">0g</span></p>
                </div>
            </div>

            <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 mb-8">
                <div class="flex items-center gap-2 mb-4">
                    <span class="text-xl">📊</span>
                    <h3 class="text-lg font-bold text-white">Relatório Comparativo e Projeção Mensal</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm border-collapse">
                        <thead>
                            <tr class="border-b border-gray-800 text-slate-400 font-semibold">
                                <th class="pb-3">Indicador de Impacto</th>
                                <th class="pb-3 text-center">Produção Atual (Real)</th>
                                <th class="pb-3 text-center text-emerald-400">Projeção 30 Dias 🚀</th>
                                <th class="pb-3 text-center text-blue-400">Meta da Usina (Ideal)</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-800/50 text-slate-300">
                            <tr>
                                <td class="py-3.5 font-medium flex items-center gap-2">⚡ Energia Acumulada</td>
                                <td class="py-3.5 text-center font-mono" id="table-real-energia">0.0000 kWh</td>
                                <td class="py-3.5 text-center font-bold text-emerald-400 font-mono" id="table-proj-energia">-- kWh</td>
                                <td class="py-3.5 text-center text-blue-400 font-mono">75.00 kWh</td>
                            </tr>
                            <tr>
                                <td class="py-3.5 font-medium flex items-center gap-2">💰 Economia Financeira</td>
                                <td class="py-3.5 text-center font-mono text-indigo-400" id="table-real-economia">R$ 0,00</td>
                                <td class="py-3.5 text-center font-bold text-emerald-400 font-mono" id="table-proj-economia">R$ --</td>
                                <td class="py-3.5 text-center text-blue-400 font-mono">R$ 71,25</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div id="historico" class="bg-gray-900 p-6 rounded-2xl border border-gray-800">
                <div class="w-full h-64"><canvas id="grafico"></canvas></div>
            </div>
        </div>

        <script>
            let chart;

            async function fetchClima() {
                try {
                    const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=-22.4256&longitude=-45.4528&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo');
                    const data = await res.json();
                    const temp = data.current.temperature_2m;
                    const code = data.current.weather_code;
                    let desc = "Estável"; let icon = "☁️";
                    if (code === 0) { desc = "Céu Limpo"; icon = "☀️"; }
                    else if (code <= 3) { desc = "Parcialmente Nublado"; icon = "⛅"; }
                    else { desc = "Chuvoso"; icon = "🌧️"; }
                    document.getElementById('weather-temp').innerText = Math.round(temp) + " °C";
                    document.getElementById('weather-desc').innerText = desc;
                    document.getElementById('weather-icon').innerText = icon;
                } catch (error) {}
            }
            fetchClima();

            async function atualizar() {
                try {
                    const res = await fetch('/api/get-luz');
                    const data = await res.json();
                    
                    if (data.status === "Online") {
                        document.getElementById('valor-luz').innerText = data.luz;
                        document.getElementById('valor-tensao').innerText = data.tensao + " V";
                        document.getElementById('valor-lux').innerText = data.lux + " Lux";
                        document.getElementById('valor-potencia').innerHTML = data.potencia_w + ' W';
                        document.getElementById('valor-energia-kwh').innerText = "Total: " + data.energia_kwh + " kWh";
                        document.getElementById('valor-economia-rs').innerText = "R$ " + data.economia_rs.substring(0,6).replace('.', ',');
                        document.getElementById('valor-co2').innerText = data.co2.replace('.', ',') + " g";
                        
                        // Atualização da Bateria
                        document.getElementById('valor-bateria').innerText = data.bateria + "%";
                        document.getElementById('barra-bateria').style.width = data.bateria + "%";
                        
                        // Atualização do Relé Dinâmico
                        const cardRele = document.getElementById('card-rele');
                        const txtRele = document.getElementById('status-rele-texto');
                        const descRele = document.getElementById('status-rele-desc');
                        
                        if(data.status_rele === 1) {
                            cardRele.className = "bg-gray-900 p-4 rounded-2xl border border-green-500/40 shadow-[0_0_15px_rgba(34,197,94,0.15)] flex flex-col justify-between transition-all";
                            txtRele.className = "text-xl font-bold text-green-400 mt-2";
                            txtRele.innerText = "ATIVADO";
                            descRele.innerText = "Despejando Excedente";
                        } else {
                            cardRele.className = "bg-gray-900 p-4 rounded-2xl border border-gray-800 flex flex-col justify-between transition-all";
                            txtRele.className = "text-xl font-bold text-slate-500 mt-2";
                            txtRele.innerText = "DESLIGADO";
                            descRele.innerText = "Acumulando na Bateria";
                        }

                        document.getElementById('table-real-energia').innerText = data.energia_kwh + " kWh";
                        document.getElementById('table-real-economia').innerText = "R$ " + data.economia_rs.substring(0,6).replace('.', ',');
                        document.getElementById('table-proj-energia').innerText = data.proj_energia.replace('.', ',') + " kWh";
                        document.getElementById('table-proj-economia').innerText = "R$ " + data.proj_economia.replace('.', ',');
                        
                        const badge = document.getElementById('badge-modo');
                        if (data.status_rele === 1) {
                            badge.className = "hidden md:flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold border border-green-500/50 bg-green-500/10 text-green-400";
                            badge.innerHTML = "🔋 Bateria Cheia / Smart Grid";
                        } else {
                            badge.className = "hidden md:flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold border border-amber-600/50 bg-amber-900/20 text-amber-400";
                            badge.innerHTML = "⏳ Carregando Armazenamento";
                        }
                        
                        // Gráfico
                        Chart.defaults.color = '#94a3b8';
                        const agora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        if(!chart) {
                            chart = new Chart(document.getElementById('grafico'), { 
                                type: 'line', 
                                data: { labels: [agora], datasets: [{ label: 'Potência (W)', data: [data.potencia_w], borderColor: '#06b6d4', backgroundColor: 'rgba(6, 182, 212, 0.15)', fill: true, tension: 0.3 }] },
                                options: { responsive: true, maintainAspectRatio: false }
                            });
                        } else {
                            chart.data.labels.push(agora);
                            chart.data.datasets[0].data.push(data.potencia_w);
                            if (chart.data.labels.length > 10) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
                            chart.update();
                        }
                    }
                } catch (error) {}
            }
            setInterval(atualizar, 2000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
