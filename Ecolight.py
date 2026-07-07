from flask import Flask, render_template_string, jsonify, request, Response
import os
import time
import io
import csv
import random

app = Flask(__name__)

# Banco de dados virtual em memória
dados_sensor = {
    "luz": 0,
    "ultima_atualizacao": 0,
    "energia_gerada_kwh": 0.0,
    "tempo_eco_acumulado": 0.0,
    "tempo_total_rodando": 0.0,
    "bateria_porcentagem": 0.0,
    "status_rele": 0,            
    "modo_operacao": "AUTO",     
    "rele_manual_cmd": 0,        
    "consumo_casa_w": 0.0,       
    "historico_dados": [],       
    "logs": []                   
}

# Constantes de Engenharia
TARIFA_KWH = 0.95
POTENCIA_MAX_W = 500.0 
EMISSAO_CO2_POR_KWH_GRAMAS = 85.0
CAPACIDADE_BATERIA_KWH = 0.05 

def adicionar_log(mensagem):
    hora_atual = time.strftime("%H:%M:%S", time.localtime())
    dados_sensor["logs"].insert(0, f"[{hora_atual}] {mensagem}")
    if len(dados_sensor["logs"]) > 30:
        dados_sensor["logs"].pop()

adicionar_log("⚙️ EcoLight Solutions: Sistema Microgrid Inicializado.")

def recalcular_energia(valor_luz):
    agora = time.time()
    if dados_sensor["ultima_atualizacao"] > 0:
        tempo_passado = agora - dados_sensor["ultima_atualizacao"]
        horas_passadas = tempo_passado / 3600.0
        
        dados_sensor["tempo_total_rodando"] += horas_passadas
        
        # --- GERAÇÃO SOLAR ---
        potencia_atual_w = (valor_luz / 1023.0) * POTENCIA_MAX_W
        potencia_atual_kw = potencia_atual_w / 1000.0
        
        # --- CONSUMO DA CASA ---
        consumo_casa_w = 120.0 + random.uniform(-5.0, 5.0)
        dados_sensor["consumo_casa_w"] = consumo_casa_w
        consumo_casa_kw = consumo_casa_w / 1000.0
        
        dados_sensor["energia_gerada_kwh"] += potencia_atual_kw * horas_passadas
        
        # Salva dados no histórico
        dados_sensor["historico_dados"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "geracao_w": round(potencia_atual_w, 1),
            "consumo_w": round(consumo_casa_w, 1),
            "bateria": round(dados_sensor["bateria_porcentagem"], 1),
            "status_rele": "LIGADO" if dados_sensor["status_rele"] == 1 else "DESLIGADO"
        })
        if len(dados_sensor["historico_dados"]) > 500:
            dados_sensor["historico_dados"].pop(0)
        
        # --- LÓGICA SMART GRID ---
        consumo_total_kw = consumo_casa_kw
        
        if dados_sensor["modo_operacao"] == "AUTO":
            if dados_sensor["status_rele"] == 0 and dados_sensor["bateria_porcentagem"] >= 100.0:
                dados_sensor["status_rele"] = 1
                adicionar_log("🔋 Bateria 100%. Algoritmo AUTO ligou a Carga Excedente.")
            elif dados_sensor["status_rele"] == 1 and dados_sensor["bateria_porcentagem"] <= 75.0:
                dados_sensor["status_rele"] = 0
                adicionar_log("📉 Bateria caiu para 75%. Algoritmo AUTO desligou a Carga Excedente.")
        else:
            dados_sensor["status_rele"] = dados_sensor["rele_manual_cmd"]

        if dados_sensor["status_rele"] == 1:
            consumo_total_kw += 0.250 

        saldo_kw = potencia_atual_kw - consumo_total_kw
        dados_sensor["bateria_porcentagem"] += (saldo_kw * horas_passadas * 100) / CAPACIDADE_BATERIA_KWH

        if dados_sensor["bateria_porcentagem"] > 100.0:
            dados_sensor["bateria_porcentagem"] = 100.0
        elif dados_sensor["bateria_porcentagem"] < 0.0:
            dados_sensor["bateria_porcentagem"] = 0.0
            
    dados_sensor["ultima_atualizacao"] = agora

@app.route("/update")
def update():
    luz_bruta = request.args.get("luz", "0")
    luz_limpa = ''.join(filter(str.isdigit, str(luz_bruta)))
    valor_final = int(luz_limpa) if luz_limpa else 0
    
    if dados_sensor["luz"] == 0 and valor_final > 0:
        adicionar_log("📡 Telemetria estabelecida com a Usina EcoLight.")
        
    recalcular_energia(valor_final)
    dados_sensor["luz"] = valor_final
    
    return f"RELE:{dados_sensor['status_rele']}"

@app.route("/api/get-luz")
def get_luz():
    agora = time.time()
    luz = dados_sensor["luz"]
    recalcular_energia(luz)
    status = "Offline" if agora - dados_sensor["ultima_atualizacao"] > 7 else "Online"
        
    tensao_calculada = (luz / 1023.0) * 3.3
    potencia_w = (luz / 1023.0) * POTENCIA_MAX_W
    energia_acumulada = dados_sensor["energia_gerada_kwh"]
    economia_rs = energia_acumulada * TARIFA_KWH
    co2_poupado = energia_acumulada * EMISSAO_CO2_POR_KWH_GRAMAS
    
    tempo_decorrido = dados_sensor["tempo_total_rodando"]
    if tempo_decorrido > 0.0001:
        proj_energia_mes = energia_acumulada * (720.0 / tempo_decorrido)
    else:
        proj_energia_mes = (potencia_w / 1000.0) * 5.0 * 30.0
        
    proj_economia_mes = proj_energia_mes * TARIFA_KWH
        
    return jsonify({
        "luz": luz,
        "status": status,
        "tensao": f"{tensao_calculada:.2f}",
        "potencia_w": f"{potencia_w:.1f}",
        "consumo_casa_w": f"{dados_sensor['consumo_casa_w']:.1f}",
        "energia_kwh": f'{energia_acumulada:.6f}', 
        "economia_rs": f'{economia_rs:.4f}',
        "co2": f"{co2_poupado:.2f}",
        "proj_energia": f"{proj_energia_mes:.2f}",
        "proj_economia": f"{proj_economia_mes:.2f}",
        "bateria": f"{dados_sensor['bateria_porcentagem']:.1f}",
        "status_rele": dados_sensor["status_rele"],
        "modo_operacao": dados_sensor["modo_operacao"],
        "logs": dados_sensor["logs"]
    })

@app.route("/api/set-modo")
def set_modo():
    modo = request.args.get("modo", "AUTO")
    if modo in ["AUTO", "MANUAL"]:
        dados_sensor["modo_operacao"] = modo
        adicionar_log(f"🔄 Modo alterado para {modo}.")
        if modo == "AUTO":
            dados_sensor["rele_manual_cmd"] = dados_sensor["status_rele"]
    return jsonify({"status": "ok"})

@app.route("/api/set-rele-manual")
def set_rele_manual():
    cmd = int(request.args.get("status", "0"))
    if dados_sensor["modo_operacao"] == "MANUAL":
        dados_sensor["rele_manual_cmd"] = cmd
        dados_sensor["status_rele"] = cmd
        adicionar_log(f"🖱️ Comando Manual: {'LIGAR' if cmd == 1 else 'DESLIGAR'} Carga Excedente.")
    return jsonify({"status": "ok"})

@app.route("/api/exportar-csv")
def exportar_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["EcoLight Solutions - Relatório de Telemetria Microgrid"])
    writer.writerow(["Timestamp", "Geração (W)", "Consumo Casa (W)", "Bateria (%)", "Relé Excedente"])
    for dado in dados_sensor["historico_dados"]:
        writer.writerow([dado["timestamp"], dado["geracao_w"], dado["consumo_w"], dado["bateria"], dado["status_rele"]])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=relatorio_ecolight_solutions.csv"})

@app.route("/api/reset")
def reset_dados():
    global dados_sensor
    dados_sensor["energia_gerada_kwh"] = 0.0
    dados_sensor["bateria_porcentagem"] = 0.0
    dados_sensor["status_rele"] = 0
    dados_sensor["modo_operacao"] = "AUTO"
    dados_sensor["rele_manual_cmd"] = 0
    dados_sensor["logs"] = []
    adicionar_log("🧹 Sistema resetado para nova demonstração institucional.")
    return jsonify({"status": "reset_ok"})

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EcoLight Solutions | EMS Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <script src="https://unpkg.com/@phosphor-icons/web"></script>
        <style>
            body { font-family: 'Inter', sans-serif; }
            .glass-panel { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(10px); }
            .custom-scroll::-webkit-scrollbar { width: 5px; }
            .custom-scroll::-webkit-scrollbar-track { background: transparent; }
            .custom-scroll::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        </style>
    </head>
    <body class="bg-[#0f1115] min-h-screen flex flex-col text-slate-200">
        <div class="max-w-7xl mx-auto p-6 flex-grow w-full">
            
            <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between mb-8 border-b border-gray-800/60 pb-5 gap-4">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-500 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.3)]">
                        <i class="ph ph-solar-panel text-2xl text-white"></i>
                    </div>
                    <div>
                        <h1 class="text-2xl font-bold text-white tracking-tight">EcoLight Solutions</h1>
                        <p class="text-xs text-cyan-400 font-medium tracking-wide uppercase">Energy Management System (EMS)</p>
                    </div>
                </div>
                
                <div class="flex flex-wrap items-center gap-3">
                    <a href="/api/exportar-csv" class="px-3 py-2 bg-gray-900 border border-gray-800 hover:border-cyan-500/50 hover:bg-cyan-500/10 rounded-lg text-xs font-semibold text-slate-300 transition-all flex items-center gap-2">
                        <i class="ph ph-file-csv text-base text-cyan-400"></i> Exportar Dados
                    </a>
                    <button onclick="resetarSistema()" class="px-3 py-2 bg-gray-900 border border-gray-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 hover:border-red-500/50 rounded-lg text-xs font-semibold transition-all flex items-center gap-2">
                        <i class="ph ph-arrows-clockwise text-base"></i> Resetar Maquete
                    </button>
                </div>
            </div>

            <div id="painel" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
                
                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-cyan-500/30 transition-all relative overflow-hidden">
                    <div class="absolute -right-4 -top-4 w-16 h-16 bg-cyan-500/5 rounded-full blur-xl"></div>
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-sun-horizon text-cyan-400 text-lg"></i> Geração Solar (Input)</p>
                    <h2 class="text-4xl font-black text-white mt-3" id="valor-potencia">0.0 W</h2>
                    <p class="text-[11px] font-medium text-slate-500 mt-2">Leitura Óptica Bruta: <span id="valor-luz" class="text-cyan-500">0</span></p>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-rose-500/30 transition-all relative overflow-hidden">
                    <div class="absolute -right-4 -top-4 w-16 h-16 bg-rose-500/5 rounded-full blur-xl"></div>
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-house-line text-rose-400 text-lg"></i> Consumo da Residência (Load)</p>
                    <h2 class="text-4xl font-black text-rose-400 mt-3" id="valor-consumo">0.0 W</h2>
                    <p class="text-[11px] font-medium text-slate-500 mt-2" id="status-balanco">Calculando balanço energético...</p>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-amber-500/40 transition-all relative overflow-hidden">
                    <div class="absolute -right-4 -top-4 w-16 h-16 bg-amber-500/5 rounded-full blur-xl"></div>
                    <div class="flex justify-between items-center">
                        <p class="text-slate-400 font-medium text-xs">Banco de Baterias (Storage)</p>
                        <i id="bateria-icon" class="ph ph-battery-charging text-amber-500 text-xl"></i>
                    </div>
                    <h2 class="text-4xl font-black text-amber-400 mt-2 tracking-tight" id="valor-bateria">0.0%</h2>
                    <div class="w-full bg-gray-800/80 h-1.5 rounded-full mt-3 overflow-hidden border border-gray-700/50">
                        <div id="barra-bateria" class="bg-gradient-to-r from-amber-600 to-amber-400 h-full transition-all duration-500 shadow-[0_0_10px_rgba(251,191,36,0.5)]" style="width: 0%"></div>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between hover:border-indigo-500/30 transition-all">
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-currency-circle-dollar text-indigo-400 text-lg"></i> Economia e Meio Ambiente</p>
                    <h2 class="text-3xl font-bold text-indigo-400 mt-3" id="valor-economia-rs">R$ 0,00</h2>
                    <div class="flex gap-2 mt-2">
                        <p class="text-[11px] text-green-400/80 font-medium bg-green-900/10 px-2 py-1 rounded border border-green-800/30 flex items-center gap-1 w-max"><i class="ph ph-leaf"></i> CO₂: <span id="valor-co2">0.0 g</span></p>
                        <p class="text-[11px] text-cyan-400/80 font-medium bg-cyan-900/10 px-2 py-1 rounded border border-cyan-800/30 flex items-center gap-1 w-max"><span id="valor-energia-kwh">0.000 kWh</span></p>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between transition-all" id="card-rele">
                    <p class="text-slate-400 font-medium text-xs flex items-center gap-2"><i class="ph ph-plug text-lg"></i> Carga Excedente (Relé)</p>
                    <h2 class="text-2xl font-bold text-slate-500 mt-3" id="status-rele-texto">DESLIGADO</h2>
                    <p class="text-[11px] text-slate-500 mt-2 font-medium" id="status-rele-desc">Acumulando na Bateria</p>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between">
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="text-xs font-bold text-slate-400 flex items-center gap-2">Modo do Relé</h3>
                        <span id="badge-modo-txt" class="text-[10px] font-bold px-2 py-0.5 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded">AUTO</span>
                    </div>
                    
                    <div class="bg-[#0b0c0f] border border-gray-800 p-1.5 rounded-xl flex items-center gap-1 mb-3">
                        <button onclick="mudarModo('AUTO')" id="btn-auto" class="flex-1 py-1.5 text-[11px] font-bold rounded-lg transition-all bg-blue-600 text-white">AUTO</button>
                        <button onclick="mudarModo('MANUAL')" id="btn-manual" class="flex-1 py-1.5 text-[11px] font-bold rounded-lg text-slate-400 hover:text-slate-200 transition-all">MANUAL</button>
                    </div>

                    <div id="controle-manual-painel" class="hidden grid-cols-2 gap-2 animate-fadeIn">
                        <button id="btn-rele-on" onclick="comandoReleManual(1)" class="py-2 bg-gray-800 text-slate-400 text-[10px] font-bold rounded-lg transition-all">LIGAR</button>
                        <button id="btn-rele-off" onclick="comandoReleManual(0)" class="py-2 bg-gray-800 text-slate-400 text-[10px] font-bold rounded-lg transition-all">DESLIGAR</button>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                <div class="glass-panel p-6 rounded-2xl border border-gray-800/80 lg:col-span-2">
                    <div class="flex items-center gap-3 mb-4">
                        <i class="ph ph-chart-line-up text-cyan-400 text-xl"></i>
                        <h3 class="text-base font-bold text-white tracking-wide">Geração Solar vs. Consumo (W)</h3>
                    </div>
                    <div class="w-full h-60"><canvas id="grafico"></canvas></div>
                </div>

                <div class="glass-panel p-6 rounded-2xl border border-gray-800/80">
                    <div class="flex items-center justify-between mb-3 pb-2 border-b border-gray-800/50">
                        <h3 class="text-sm font-bold text-white flex items-center gap-2"><i class="ph ph-terminal text-emerald-400"></i> Histórico de Eventos</h3>
                        <i class="ph ph-circle text-[8px] text-emerald-400 animate-ping"></i>
                    </div>
                    <div id="log-container" class="h-52 overflow-y-auto custom-scroll font-mono text-xs text-slate-400 flex flex-col gap-2.5 pr-2">
                    </div>
                </div>
            </div>
        </div>

        <script>
            let chart;

            async function mudarModo(novoModo) {
                await fetch(`/api/set-modo?modo=${novoModo}`);
                atualizarInterfaceModo(novoModo);
            }

            async function comandoReleManual(status) {
                await fetch(`/api/set-rele-manual?status=${status}`);
            }

            function atualizarInterfaceModo(modo) {
                const btnAuto = document.getElementById('btn-auto');
                const btnManual = document.getElementById('btn-manual');
                const painelManual = document.getElementById('controle-manual-painel');
                const badgeModo = document.getElementById('badge-modo-txt');

                if (modo === "AUTO") {
                    btnAuto.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg transition-all bg-blue-600 text-white";
                    btnManual.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg text-slate-400 transition-all";
                    painelManual.classList.remove('grid');
                    painelManual.classList.add('hidden');
                    badgeModo.className = "text-[10px] font-bold px-2 py-0.5 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded";
                    badgeModo.innerText = "AUTO";
                } else {
                    btnManual.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg transition-all bg-amber-500 text-slate-950";
                    btnAuto.className = "flex-1 py-1.5 text-[11px] font-bold rounded-lg text-slate-400 transition-all";
                    painelManual.classList.remove('hidden');
                    painelManual.classList.add('grid');
                    badgeModo.className = "text-[10px] font-bold px-2 py-0.5 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded";
                    badgeModo.innerText = "MANUAL";
                }
            }

            async function resetarSistema() {
                if(confirm("Zerar dados da maquete?")) {
                    await fetch('/api/reset');
                    window.location.reload();
                }
            }

            async function atualizar() {
                try {
                    const res = await fetch('/api/get-luz');
                    const data = await res.json();
                    
                    if (data.status === "Online") {
                        document.getElementById('valor-luz').innerText = data.luz;
                        document.getElementById('valor-potencia').innerHTML = data.potencia_w + ' W';
                        document.getElementById('valor-consumo').innerHTML = data.consumo_casa_w + ' W';
                        
                        const geracao = parseFloat(data.potencia_w);
                        const consumo = parseFloat(data.consumo_casa_w);
                        const balancoTxt = document.getElementById('status-balanco');
                        
                        if(geracao > consumo) {
                            balancoTxt.innerHTML = `<span class="text-green-400">Restam +${(geracao-consumo).toFixed(1)}W (Carregando Bateria)</span>`;
                        } else {
                            balancoTxt.innerHTML = `<span class="text-amber-400">Faltam ${(consumo-geracao).toFixed(1)}W (Usando Bateria)</span>`;
                        }

                        document.getElementById('valor-energia-kwh').innerText = parseFloat(data.energia_kwh).toFixed(3) + " kWh";
                        document.getElementById('valor-economia-rs').innerText = "R$ " + parseFloat(data.economia_rs.replace(',','.')).toFixed(2).replace('.', ',');
                        document.getElementById('valor-co2').innerText = parseFloat(data.co2).toFixed(1).replace('.', ',') + " g";
                        
                        document.getElementById('valor-bateria').innerText = data.bateria + "%";
                        document.getElementById('barra-bateria').style.width = data.bateria + "%";
                        
                        const logContainer = document.getElementById('log-container');
                        logContainer.innerHTML = data.logs.map(log => `<div>${log}</div>`).join('');

                        if(data.modo_operacao === "MANUAL") {
                            atualizarInterfaceModo("MANUAL");
                            if(data.status_rele === 1) {
                                document.getElementById('btn-rele-on').className = "py-2 bg-green-500/20 text-green-400 border border-green-500 text-[10px] font-bold rounded-lg transition-all";
                                document.getElementById('btn-rele-off').className = "py-2 bg-gray-800 text-slate-500 border border-gray-700 text-[10px] font-bold rounded-lg transition-all";
                            } else {
                                document.getElementById('btn-rele-off').className = "py-2 bg-red-500/20 text-red-400 border border-red-500 text-[10px] font-bold rounded-lg transition-all";
                                document.getElementById('btn-rele-on').className = "py-2 bg-gray-800 text-slate-500 border border-gray-700 text-[10px] font-bold rounded-lg transition-all";
                            }
                        } else {
                            atualizarInterfaceModo("AUTO");
                        }
                        
                        const batIcon = document.getElementById('bateria-icon');
                        if(parseFloat(data.bateria) >= 100) batIcon.className = "ph ph-battery-full text-green-400 text-2xl drop-shadow-[0_0_8px_rgba(74,222,128,0.8)]";
                        else if(parseFloat(data.bateria) > 20) batIcon.className = "ph ph-battery-charging text-amber-400 text-2xl";
                        else batIcon.className = "ph ph-battery-warning text-red-500 text-2xl animate-pulse";
                        
                        const cardRele = document.getElementById('card-rele');
                        const txtRele = document.getElementById('status-rele-texto');
                        
                        if(data.status_rele === 1) {
                            cardRele.className = "glass-panel p-5 rounded-2xl border border-green-500/50 shadow-[0_0_20px_rgba(34,197,94,0.15)] flex flex-col justify-between transition-all";
                            txtRele.className = "text-2xl font-bold text-green-400 mt-3";
                            txtRele.innerHTML = "ATIVADO";
                        } else {
                            cardRele.className = "glass-panel p-5 rounded-2xl border border-gray-800/80 flex flex-col justify-between transition-all";
                            txtRele.className = "text-2xl font-bold text-slate-500 mt-3";
                            txtRele.innerHTML = "DESLIGADO";
                        }

                        // GRÁFICO DUPLO
                        Chart.defaults.color = '#64748b';
                        Chart.defaults.font.family = 'Inter';
                        const agora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        
                        if(!chart) {
                            const ctx = document.getElementById('grafico').getContext('2d');
                            
                            let gradSolar = ctx.createLinearGradient(0, 0, 0, 400);
                            gradSolar.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
                            gradSolar.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

                            let gradConsumo = ctx.createLinearGradient(0, 0, 0, 400);
                            gradConsumo.addColorStop(0, 'rgba(244, 63, 94, 0.4)');
                            gradConsumo.addColorStop(1, 'rgba(244, 63, 94, 0.0)');
                            
                            chart = new Chart(ctx, { 
                                type: 'line', 
                                data: { 
                                    labels: [agora], 
                                    datasets: [
                                        { label: 'Geração Solar', data: [geracao], borderColor: '#06b6d4', backgroundColor: gradSolar, borderWidth: 2, fill: true, tension: 0.4, pointRadius: 0 },
                                        { label: 'Consumo Casa', data: [consumo], borderColor: '#f43f5e', backgroundColor: gradConsumo, borderWidth: 2, fill: true, tension: 0.4, pointRadius: 0 }
                                    ] 
                                },
                                options: { 
                                    responsive: true, maintainAspectRatio: false,
                                    plugins: { legend: { display: true, labels: { color: '#cbd5e1' } } },
                                    scales: { y: { border: {dash: [4, 4]}, grid: {color: '#1e293b'} }, x: { grid: {display: false} } }
                                }
                            });
                        } else {
                            chart.data.labels.push(agora);
                            chart.data.datasets[0].data.push(geracao);
                            chart.data.datasets[1].data.push(consumo);
                            if (chart.data.labels.length > 20) { 
                                chart.data.labels.shift(); 
                                chart.data.datasets[0].data.shift(); 
                                chart.data.datasets[1].data.shift(); 
                            }
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
