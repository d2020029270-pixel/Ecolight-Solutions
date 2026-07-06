from flask import Flask, render_template_string, jsonify, request
import os
import time

app = Flask(__name__)

# Dicionário global com o banco de baterias virtual e telemetria
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0,
    "energia_gerada_kwh": 0.0,
    "tempo_eco_acumulado": 0.0,
    "tempo_total_rodando": 0.0,
    "bateria_porcentagem": 0.0, # Estado de carga da bateria (0 a 100%)
    "status_rele": 0            # 0 = Desligado, 1 = Ligado (Descarte/Smart Grid)
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
        
        # Geração atual baseada no LDR
        potencia_atual_w = (valor_luz / 1023.0) * POTENCIA_MAX_W
        potencia_atual_kw = potencia_atual_w / 1000.0
        
        # Acumula energia total gerada
        dados_sensor["energia_gerada_kwh"] += potencia_atual_kw * horas_passadas
        
        # --- LÓGICA DA BATERIA VIRTUAL E AUTOMAÇÃO (CARREGAMENTO LENTO) ---
        # Multiplicador definido em 100 para levar de 5 a 6 minutos sob luz forte
        if dados_sensor["status_rele"] == 0:
            dados_sensor["bateria_porcentagem"] += (potencia_atual_kw * horas_passadas * 100) / CAPACIDADE_BATERIA_KWH
            if dados_sensor["bateria_porcentagem"] >= 100.0:
                dados_sensor["bateria_porcentagem"] = 100.0
                dados_sensor["status_rele"] = 1 # Bateria cheia! Ativa o descarte
        else:
            # Se o relé está ligado, simula o consumo de um aparelho
            consumo_aparelho_kw = 0.250 # Aparelho simulado consome 250W
            saldo_energia = potencia_atual_kw - consumo_aparelho_kw
            dados_sensor["bateria_porcentagem"] += (saldo_energia * horas_passadas * 100) / CAPACIDADE_BATERIA_KWH
            
            # Limite de segurança para desligar o relé e voltar a acumular
            if dados_sensor["bateria_porcentagem"] <= 75.0:
                dados_sensor["status_rele"] = 0
                
        # Trava de segurança para limites físicos da bateria
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

@app.route("/api/reset")
def reset_dados():
    global dados_sensor
    dados_sensor["energia_gerada_kwh"] = 0.0
    dados_sensor["tempo_eco_acumulado"] = 0.0
    dados_sensor["tempo_total_rodando"] = 0.0
    dados_sensor["bateria_porcentagem"] = 0.0
    dados_sensor["status_rele"] = 0
    return jsonify({"status": "reset_ok"})

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
        
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        
        <script src="https://unpkg.com/@phosphor-icons/web"></script>
        
        <style>
            body { font-family: 'Inter', sans-serif; }
            .glass-panel { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(10px); }
        </style>
    </head>
    <body class="bg-[#0f1115] min-h-screen flex flex-col text-slate-200">
        <div class="max-w-6xl mx-auto p-6 flex-grow w-full">
            
            <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-8 border-b border-gray-800/60 pb-5 gap-4">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(37,99,235,0.4)]">
                        <i class="ph ph-solar-panel text-2xl text-white"></i>
                    </div>
                    <div>
                        <h1 class="text-2xl font-bold text-white tracking-tight">EcoLight Solar</h1>
                        <p class="text-xs text-blue-400 font-medium tracking-wide uppercase">Telemetria & BMS IoT</p>
                    </div>
                </div>
                
                <div class="flex items-center gap-3">
                    <button onclick="resetarSistema()" class="px-3 py-2 bg-gray-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-gray-700 hover:border-red-500/50 rounded-lg text-xs font-semibold transition-all flex items-center gap-2">
                        <i class="ph ph-arrows-clockwise text-base"></i> Resetar Maquete
                    </button>
                    
                    <div class="flex items-center gap-3 px-4 py-2 rounded-xl glass-panel border border-gray-800 shadow-sm">
                        <i id="weather-icon" class="ph ph-cloud-sun text-2xl text-slate-300"></i>
                        <div>
                            <p class="text-[10px] text-slate-500 font-bold tracking-wider">ITAJUBÁ, MG</p>
                            <p class="text-sm font-bold text-white"><span id="weather-temp">-- °C</span> <span class="text-xs text-slate-400 font-normal ml-1" id="weather-desc">Buscando...</span></p>
                        </div>
                    </div>
                    <div id="badge-modo" class="hidden md:flex px-4 py-2 rounded-xl text-xs font-bold border transition-all duration-300">--</div>
                </div>
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
                
                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-blue-500/30 transition-all">
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-sun text-blue-400 text-lg"></i> Leitura Óptica</p>
                    <h2 class="text-4xl font-black text-white mt-3 tracking-tight" id="valor-luz">--</h2>
                    <div class="flex gap-3 mt-2">
                        <p class="text-xs font-semibold text-slate-300 bg-gray-800 px-2 py-1 rounded" id="valor-tensao">0.00 V</p>
                        <p class="text-xs font-semibold text-amber-400/90 bg-amber-900/20 px-2 py-1 rounded" id="valor-lux">0 Lux</p>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-cyan-500/30 transition-all">
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-lightning text-cyan-400 text-lg"></i> Geração Solar</p>
                    <h2 class="text-3xl font-bold text-white mt-3" id="valor-potencia">0.0 W</h2>
                    <p class="text-[11px] font-medium text-cyan-500 mt-2" id="valor-energia-kwh">Total: 0.000 kWh</p>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-amber-500/40 transition-all shadow-[0_0_15px_rgba(0,0,0,0.5)] relative overflow-hidden">
                    <div class="absolute -right-4 -top-4 w-16 h-16 bg-amber-500/5 rounded-full blur-xl"></div>
                    <div class="flex justify-between items-center">
                        <p class="text-slate-400 font-medium text-xs">Banco de Baterias</p>
                        <i id="bateria-icon" class="ph ph-battery-charging text-amber-500 text-xl"></i>
                    </div>
                    <h2 class="text-4xl font-black text-amber-400 mt-2 tracking-tight" id="valor-bateria">0.0%</h2>
                    <div class="w-full bg-gray-800/80 h-1.5 rounded-full mt-3 overflow-hidden border border-gray-700/50">
                        <div id="barra-bateria" class="bg-gradient-to-r from-amber-600 to-amber-400 h-full transition-all duration-500 shadow-[0_0_10px_rgba(251,191,36,0.5)]" style="width: 0%"></div>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between transition-all" id="card-rele">
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-plug text-lg"></i> Carga Excedente (Relé)</p>
                    <h2 class="text-2xl font-bold text-slate-500 mt-3" id="status-rele-texto">DESLIGADO</h2>
                    <p class="text-[11px] text-slate-500 mt-2 font-medium" id="status-rele-desc">Acumulando na Bateria</p>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-indigo-500/30 transition-all">
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-currency-circle-dollar text-indigo-400 text-lg"></i> Economia Total</p>
                    <h2 class="text-3xl font-bold text-indigo-400 mt-3" id="valor-economia-rs">R$ 0,00</h2>
                    <p class="text-[11px] text-green-400/80 mt-2 font-medium bg-green-900/10 inline-block px-2 py-1 rounded border border-green-800/30 flex items-center gap-1 w-max">
                        <i class="ph ph-leaf"></i> CO₂: <span id="valor-co2">0.0 g</span>
                    </p>
                </div>
            </div>

            <div class="glass-panel p-6 rounded-2xl border border-gray-800/80 mb-8">
                <div class="flex items-center gap-3 mb-5 border-b border-gray-800/50 pb-4">
                    <div class="p-2 bg-gray-800 rounded-lg"><i class="ph ph-chart-bar text-xl text-slate-300"></i></div>
                    <h3 class="text-base font-bold text-white tracking-wide">Relatório Comparativo e Projeção Mensal</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm border-collapse">
                        <thead>
                            <tr class="border-b border-gray-800/60 text-slate-400 font-medium text-xs uppercase tracking-wider">
                                <th class="pb-3 pl-2">Indicador de Impacto</th>
                                <th class="pb-3 text-center">Produção Atual (Real)</th>
                                <th class="pb-3 text-center text-emerald-400">Projeção 30 Dias</th>
                                <th class="pb-3 text-center text-blue-400/80">Meta da Usina (Ideal)</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-800/40 text-slate-300">
                            <tr class="hover:bg-gray-800/20 transition-colors">
                                <td class="py-4 pl-2 font-medium flex items-center gap-3"><i class="ph ph-lightning text-lg text-slate-500"></i> Energia Acumulada</td>
                                <td class="py-4 text-center font-mono text-sm" id="table-real-energia">0.000 kWh</td>
                                <td class="py-4 text-center font-bold text-emerald-400 font-mono text-sm" id="table-proj-energia">0.00 kWh</td>
                                <td class="py-4 text-center text-blue-400/80 font-mono text-sm">75.00 kWh</td>
                            </tr>
                            <tr class="hover:bg-gray-800/20 transition-colors">
                                <td class="py-4 pl-2 font-medium flex items-center gap-3"><i class="ph ph-money text-lg text-slate-500"></i> Economia Financeira</td>
                                <td class="py-4 text-center font-mono text-indigo-400 text-sm" id="table-real-economia">R$ 0,00</td>
                                <td class="py-4 text-center font-bold text-emerald-400 font-mono text-sm" id="table-proj-economia">R$ 0,00</td>
                                <td class="py-4 text-center text-blue-400/80 font-mono text-sm">R$ 71,25</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div id="historico" class="glass-panel p-6 rounded-2xl border border-gray-800/80">
                <div class="flex items-center gap-3 mb-4">
                    <i class="ph ph-trend-up text-cyan-400 text-xl"></i>
                    <h3 class="text-base font-bold text-white tracking-wide">Potência em Tempo Real (W)</h3>
                </div>
                <div class="w-full h-60"><canvas id="grafico"></canvas></div>
            </div>
        </div>

        <script>
            let chart;

            async function resetarSistema() {
                if(confirm("Deseja zerar todos os dados para uma nova apresentação?")) {
                    await fetch('/api/reset');
                    if(chart) {
                        chart.data.labels = [];
                        chart.data.datasets[0].data = [];
                        chart.update();
                    }
                    window.location.reload();
                }
            }

            async function fetchClima() {
                try {
                    const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=-22.4256&longitude=-45.4528&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo');
                    const data = await res.json();
                    const temp = data.current.temperature_2m;
                    const code = data.current.weather_code;
                    let desc = "Estável"; let icon = "ph-cloud-sun";
                    if (code === 0) { desc = "Céu Limpo"; icon = "ph-sun"; }
                    else if (code <= 3) { desc = "Parc. Nublado"; icon = "ph-cloud-sun"; }
                    else { desc = "Chuvoso"; icon = "ph-cloud-rain"; }
                    document.getElementById('weather-temp').innerText = Math.round(temp) + " °C";
                    document.getElementById('weather-desc').innerText = desc;
                    document.getElementById('weather-icon').className = `ph ${icon} text-2xl text-blue-300`;
                } catch (error) {}
            }
            fetchClima();

            async function atualizar() {
                try {
                    const res = await fetch('/api/get-luz');
                    const data = await res.json();
                    
                    if (data.status === "Online") {
                        // ARREDONDAMENTO DAS CASAS DECIMAIS VIA JAVASCRIPT
                        const energiaReal = parseFloat(data.energia_kwh).toFixed(3);
                        const energiaProj = parseFloat(data.proj_energia).toFixed(2);
                        const econReal = parseFloat(data.economia_rs.replace(',','.')).toFixed(2);
                        const econProj = parseFloat(data.proj_economia.replace(',','.')).toFixed(2);
                        const co2Real = parseFloat(data.co2.replace(',','.')).toFixed(1);

                        document.getElementById('valor-luz').innerText = data.luz;
                        document.getElementById('valor-tensao').innerText = data.tensao + " V";
                        document.getElementById('valor-lux').innerText = data.lux + " Lux";
                        document.getElementById('valor-potencia').innerHTML = data.potencia_w + ' W';
                        
                        document.getElementById('valor-energia-kwh').innerText = "Total: " + energiaReal + " kWh";
                        document.getElementById('valor-economia-rs').innerText = "R$ " + econReal.replace('.', ',');
                        document.getElementById('valor-co2').innerText = co2Real.replace('.', ',') + " g";
                        
                        document.getElementById('valor-bateria').innerText = data.bateria + "%";
                        document.getElementById('barra-bateria').style.width = data.bateria + "%";
                        
                        // Troca dinâmica do ícone da bateria com efeito glow
                        const batIcon = document.getElementById('bateria-icon');
                        if(parseFloat(data.bateria) >= 100) batIcon.className = "ph ph-battery-full text-green-400 text-2xl drop-shadow-[0_0_8px_rgba(74,222,128,0.8)]";
                        else if(parseFloat(data.bateria) > 20) batIcon.className = "ph ph-battery-charging text-amber-400 text-2xl";
                        else batIcon.className = "ph ph-battery-warning text-red-500 text-2xl animate-pulse";
                        
                        const cardRele = document.getElementById('card-rele');
                        const txtRele = document.getElementById('status-rele-texto');
                        const descRele = document.getElementById('status-rele-desc');
                        
                        if(data.status_rele === 1) {
                            cardRele.className = "glass-panel p-5 rounded-2xl border border-green-500/50 shadow-[0_0_20px_rgba(34,197,94,0.15)] flex flex-col justify-between transition-all";
                            txtRele.className = "text-2xl font-bold text-green-400 mt-3 tracking-wide";
                            txtRele.innerHTML = "ATIVADO";
                            descRele.className = "text-[11px] text-green-400/80 mt-2 font-medium";
                            descRele.innerText = "Despejando Excedente (Smart Grid)";
                        } else {
                            cardRele.className = "glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between transition-all";
                            txtRele.className = "text-2xl font-bold text-slate-500 mt-3 tracking-wide";
                            txtRele.innerHTML = "DESLIGADO";
                            descRele.className = "text-[11px] text-slate-500 mt-2 font-medium";
                            descRele.innerText = "Acumulando na Bateria";
                        }

                        document.getElementById('table-real-energia').innerText = energiaReal + " kWh";
                        document.getElementById('table-real-economia').innerText = "R$ " + econReal.replace('.', ',');
                        document.getElementById('table-proj-energia').innerText = energiaProj.replace('.', ',') + " kWh";
                        document.getElementById('table-proj-economia').innerText = "R$ " + econProj.replace('.', ',');
                        
                        const badge = document.getElementById('badge-modo');
                        if (data.status_rele === 1) {
                            badge.className = "hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] uppercase tracking-wider font-bold border border-green-500/50 bg-green-500/10 text-green-400";
                            badge.innerHTML = '<i class="ph ph-check-circle text-base"></i> Bateria 100%';
                        } else {
                            badge.className = "hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] uppercase tracking-wider font-bold border border-amber-500/30 bg-amber-900/20 text-amber-400";
                            badge.innerHTML = '<i class="ph ph-hourglass-low text-base animate-pulse"></i> Carregando';
                        }
                        
                        // Atualização do gráfico com curvas suaves e degradê
                        Chart.defaults.color = '#64748b';
                        Chart.defaults.font.family = 'Inter';
                        const agora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        
                        if(!chart) {
                            const ctx = document.getElementById('grafico').getContext('2d');
                            let gradient = ctx.createLinearGradient(0, 0, 0, 400);
                            gradient.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
                            gradient.addColorStop(1, 'rgba(6, 182, 212, 0.0)');
                            
                            chart = new Chart(ctx, { 
                                type: 'line', 
                                data: { labels: [agora], datasets: [{ label: 'Potência (W)', data: [data.potencia_w], borderColor: '#06b6d4', backgroundColor: gradient, borderWidth: 2, fill: true, tension: 0.4, pointRadius: 0, pointHitRadius: 10 }] },
                                options: { 
                                    responsive: true, maintainAspectRatio: false,
                                    plugins: { legend: { display: false } },
                                    scales: { y: { border: {dash: [4, 4]}, grid: {color: '#1e293b'} }, x: { grid: {display: false} } }
                                }
                            });
                        } else {
                            chart.data.labels.push(agora);
                            chart.data.datasets[0].data.push(data.potencia_w);
                            if (chart.data.labels.length > 15) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
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
