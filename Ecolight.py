from flask import Flask, render_template_string, jsonify, request
import os
import time

app = Flask(__name__)

# Dicionário global
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0,
    "energia_gerada_kwh": 0.0,
    "tempo_eco_acumulado": 0.0,
    "tempo_total_rodando": 0.0  # Necessário para calcular a taxa de projeção mensal
}

# Constantes de Engenharia para a Simulação Solar
TARIFA_KWH = 0.95
POTENCIA_MAX_W = 500.0 # Painel simulado de 500 Watts
EMISSAO_CO2_POR_KWH_GRAMAS = 85.0

def recalcular_energia(valor_luz):
    agora = time.time()
    if dados_sensor["ultima_atualizacao"] > 0:
        tempo_passado = agora - dados_sensor["ultima_atualizacao"]
        horas_passadas = tempo_passado / 3600.0
        
        # Registra o tempo total que o servidor está coletando dados
        dados_sensor["tempo_total_rodando"] += horas_passadas
        
        # Calcula a potência gerada instantânea baseada na luz (0 a 500W)
        potencia_atual_w = (valor_luz / 1023.0) * POTENCIA_MAX_W
        potencia_atual_kw = potencia_atual_w / 1000.0
        
        # Acumula a energia gerada (kWh)
        dados_sensor["energia_gerada_kwh"] += potencia_atual_kw * horas_passadas
        
        # Se está gerando energia (Luz > 300), conta como tempo sustentável
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
    return "OK"

@app.route("/api/get-luz")
def get_luz():
    agora = time.time()
    luz = dados_sensor["luz"]
    
    recalcular_energia(luz)
    status = "Offline" if agora - dados_sensor["ultima_atualizacao"] > 7 else "Online"
        
    taxa_eficiencia = round((luz / 1024.0) * 100)
    taxa_eficiencia = max(0, min(100, taxa_eficiencia))
    
    # Cálculos Físicos
    tensao_calculada = (luz / 1023.0) * 3.3
    tensao_calculada = max(0.0, min(3.3, tensao_calculada))
    
    # Estimativa de Iluminância em Lux e Geração Instantânea em Watts
    lux_estimado = int((luz / 1023.0) * 1000)
    potencia_w = (luz / 1023.0) * POTENCIA_MAX_W
    
    # Cálculo Financeiro (Dinheiro Economizado/Gerado) e Sustentabilidade
    energia_acumulada = dados_sensor["energia_gerada_kwh"]
    economia_rs = energia_acumulada * TARIFA_KWH
    co2_poupado = energia_acumulada * EMISSAO_CO2_POR_KWH_GRAMAS
    
    # Lógica de Projeção Mensal Baseada no Histórico Real de Execução (30 dias = 720 horas)
    tempo_decorrido = dados_sensor["tempo_total_rodando"]
    if tempo_decorrido > 0.0001:
        fator_mensal = 720.0 / tempo_decorrido
        proj_energia_mes = energia_acumulada * fator_mensal
    else:
        # Fallback inicial caso acabe de ligar o servidor
        proj_energia_mes = (potencia_w / 1000.0) * 5.0 * 30.0 # Simula 5h de sol por dia
        
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
        
        # Dados do Resumo Mensal Projetado
        "proj_energia": f"{proj_energia_mes:.2f}",
        "proj_economia": f"{proj_economia_mes:.2f}",
        "proj_co2": f"{proj_co2_mes:.1f}"
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
                        <p class="text-sm text-blue-400 font-medium">Telemetria de Geração Fotovoltaica</p>
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

                    <div id="badge-modo" class="hidden md:flex px-4 py-2.5 rounded-xl text-sm font-bold border transition-all duration-300">
                        --
                    </div>
                </div>
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                
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

                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-cyan-500/50 transition-colors relative overflow-hidden">
                    <div class="absolute -right-4 -top-4 w-16 h-16 bg-cyan-500/10 rounded-full blur-xl"></div>
                    <div class="flex items-center justify-between mb-4 relative">
                        <p class="text-slate-400 font-semibold text-sm">Geração do Painel</p>
                        <div class="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20"><svg class="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg></div>
                    </div>
                    <div class="relative">
                        <h2 class="text-4xl font-bold text-white" id="valor-potencia">0.0 <span class="text-lg text-slate-400 font-medium">W</span></h2>
                        <p class="text-xs font-semibold text-cyan-400 mt-2 bg-cyan-900/30 inline-block px-2 py-1 rounded border border-cyan-800/50" id="valor-energia-kwh">Total: 0.000000 kWh</p>
                    </div>
                </div>

                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-indigo-500/50 transition-colors">
                    <div class="flex items-center justify-between mb-4">
                        <p class="text-slate-400 font-semibold text-sm">Valor Gerado</p>
                        <div class="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20"><svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></div>
                    </div>
                    <h2 class="text-3xl font-bold text-indigo-400" id="valor-economia-rs">R$ 0,00</h2>
                </div>

                <div class="bg-gray-900 p-5 rounded-2xl shadow-sm border border-gray-800 flex flex-col justify-between hover:border-teal-500/50 transition-colors">
                    <div class="flex items-center justify-between mb-2">
                        <p class="text-slate-400 font-semibold text-sm">Capacidade da Usina</p>
                        <div class="p-2 bg-teal-500/10 rounded-lg border border-teal-500/20"><svg class="w-5 h-5 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg></div>
                    </div>
                    <div>
                        <h2 class="text-3xl font-black text-teal-400" id="valor-eficiencia">--%</h2>
                        <div class="w-full bg-gray-800 rounded-full h-2 mt-2">
                            <div class="bg-teal-500 h-2 rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(20,184,166,0.6)]" id="barra-eficiencia" style="width: 0%"></div>
                        </div>
                        <div class="mt-3 flex justify-between items-center text-xs font-semibold text-slate-400 bg-gray-800/50 px-3 py-2 rounded-lg border border-gray-700/50">
                            <span>🌿 CO₂ Evitado:</span>
                            <span class="text-green-400" id="valor-co2">0.00 g</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-gray-900 p-6 rounded-2xl border border-gray-800 mb-8 hover:border-emerald-500/30 transition-colors">
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
                            <tr>
                                <td class="py-3.5 font-medium flex items-center gap-2">🌱 Carbono Evitado (CO₂)</td>
                                <td class="py-3.5 text-center font-mono text-green-400" id="table-real-co2">0.00 g</td>
                                <td class="py-3.5 text-center font-bold text-emerald-400 font-mono" id="table-proj-co2">-- g</td>
                                <td class="py-3.5 text-center text-blue-400 font-mono">6.37 kg</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <p class="text-[11px] text-slate-500 mt-3 italic text-right">*Projeções calculadas dinamicamente via algoritmo preditivo com base na taxa de irradiância lida pelo LDR.</p>
            </div>

            <div id="historico" class="bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-800">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-white">Gráfico de Potência Instantânea</h3>
                    <span class="text-xs font-semibold text-cyan-400 bg-cyan-900/30 border border-cyan-800/50 px-3 py-1 rounded-full">Watts Gerados</span>
                </div>
                <div class="w-full h-64">
                    <canvas id="grafico"></canvas>
                </div>
            </div>
        </div>

        <script>
            let chart;

            // Função para buscar o clima de Itajubá-MG
            async function fetchClima() {
                try {
                    const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=-22.4256&longitude=-45.4528&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo');
                    const data = await res.json();
                    const temp = data.current.temperature_2m;
                    const code = data.current.weather_code;
                    
                    let desc = "Estável"; let icon = "☁️";
                    if (code === 0) { desc = "Céu Limpo"; icon = "☀️"; }
                    else if (code <= 3) { desc = "Parcialmente Nublado"; icon = "⛅"; }
                    else if (code <= 48) { desc = "Neblina"; icon = "🌫️"; }
                    else if (code <= 67) { desc = "Chuvoso"; icon = "🌧️"; }
                    else if (code <= 77) { desc = "Frio Extremo"; icon = "❄️"; }
                    else { desc = "Tempestade"; icon = "⛈️"; }

                    document.getElementById('weather-temp').innerText = Math.round(temp) + " °C";
                    document.getElementById('weather-desc').innerText = desc;
                    document.getElementById('weather-icon').innerText = icon;
                } catch (error) {
                    console.error("Erro ao carregar clima:", error);
                }
            }

            fetchClima();
            setInterval(fetchClima, 30 * 60 * 1000);

            async function atualizar() {
                try {
                    const res = await fetch('/api/get-luz');
                    const data = await res.json();
                    
                    if (data.status === "Online") {
                        // Atualização dos Cards
                        document.getElementById('valor-luz').innerText = data.luz;
                        document.getElementById('valor-tensao').innerText = data.tensao + " V";
                        document.getElementById('valor-lux').innerText = data.lux + " Lux";
                        
                        document.getElementById('valor-potencia').innerHTML = data.potencia_w + ' <span class="text-lg text-slate-400 font-medium">W</span>';
                        document.getElementById('valor-energia-kwh').innerText = "Total: " + data.energia_kwh + " kWh";
                        document.getElementById('valor-economia-rs').innerText = "R$ " + data.economia_rs.replace('.', ',');
                        
                        document.getElementById('valor-eficiencia').innerText = data.eficiencia + "%";
                        document.getElementById('barra-eficiencia').style.width = data.eficiencia + "%";
                        document.getElementById('valor-co2').innerText = data.co2.replace('.', ',') + " g";
                        
                        // Atualização da Tabela de Resumo/Projeção Mensal
                        document.getElementById('table-real-energia').innerText = data.energia_kwh + " kWh";
                        document.getElementById('table-real-economia').innerText = "R$ " + data.economia_rs.substring(0,6).replace('.', ',');
                        document.getElementById('table-real-co2').innerText = data.co2.replace('.', ',') + " g";
                        
                        document.getElementById('table-proj-energia').innerText = data.proj_energia.replace('.', ',') + " kWh";
                        document.getElementById('table-proj-economia').innerText = "R$ " + data.proj_economia.replace('.', ',');
                        document.getElementById('table-proj-co2').innerText = (parseFloat(data.proj_co2) >= 1000) ? (parseFloat(data.proj_co2)/1000).toFixed(2).replace('.', ',') + " kg" : data.proj_co2.replace('.', ',') + " g";
                        
                        // Badge Dinâmico
                        const badge = document.getElementById('badge-modo');
                        if (data.luz >= 100) {
                            badge.className = "hidden md:flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold border border-green-500/50 bg-green-500/10 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.2)]";
                            badge.innerHTML = "☀️ Gerando Energia";
                        } else {
                            badge.className = "hidden md:flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold border border-slate-600/50 bg-slate-800/80 text-slate-400";
                            badge.innerHTML = "🌙 Baixa Captação";
                        }
                        
                        // Gráfico Dark Mode
                        Chart.defaults.color = '#94a3b8';
                        Chart.defaults.borderColor = '#334155';
                        
                        const agora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        if(!chart) {
                            chart = new Chart(document.getElementById('grafico'), { 
                                type: 'line', 
                                data: { labels: [agora], datasets: [{ label: 'Potência (W)', data: [data.potencia_w], borderColor: '#06b6d4', backgroundColor: 'rgba(6, 182, 212, 0.15)', fill: true, tension: 0.3, pointBackgroundColor: '#22d3ee' }] },
                                options: { 
                                    responsive: true, 
                                    maintainAspectRatio: false, 
                                    scales: { 
                                        y: { min: 0, max: 500, grid: {color: '#1e293b'} }, 
                                        x: { grid: {color: '#1e293b'} } 
                                    } 
                                }
                            });
                        } else {
                            chart.data.labels.push(agora);
                            chart.data.datasets[0].data.push(data.potencia_w);
                            
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
