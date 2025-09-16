import os
import datetime
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =========================
# CONFIGURAÇÕES
# =========================
# As chaves e IDs são lidos das variáveis de ambiente
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
TEAM_ID = 118  # Bahia
LEAGUE_ID = 71 # Serie A (Brasil)
SEASON = 2023  # Ano permitido no plano gratuito da API

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# =========================
# FUNÇÕES DE APOIO
# =========================
def get_data(endpoint: str, params: dict):
    """Função genérica para buscar dados da API e tratar erros"""
    try:
        url = f"{BASE_URL}/{endpoint}"
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()  # Lança um erro para status 4xx ou 5xx
        return resp.json().get("response", [])
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição para a API: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Erro ao processar a resposta da API: {e}")
        return None

# =========================
# COMANDOS DO BOT
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚽ Olá, eu sou o bot do Bahia!\nDigite /ajuda para ver os comandos.")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comandos = """
📌 Comandos disponíveis:
/estatisticas - Resumo da temporada 2023
/jogos - Lista todos os jogos da temporada
/proximo - Mostra o próximo jogo
/vitorias - Lista os times que o Bahia venceu
/artilheiro - Mostra o artilheiro do Bahia
/assistencias - Mostra o líder em assistências
"""
    await update.message.reply_text(comandos)

async def estatisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_data("teams/statistics", {"league": LEAGUE_ID, "team": TEAM_ID, "season": SEASON})
    if not stats:
        await update.message.reply_text("❌ Não consegui buscar as estatísticas. A temporada pode ter sido finalizada ou houve um erro na API.")
        return

    resumo = stats.get("fixtures", {})
    gols = stats.get("goals", {})

    msg = f"""
📊 Estatísticas do Bahia ({SEASON}):
🏆 Vitórias: {resumo.get('wins', {}).get('total', '0')}
🤝 Empates: {resumo.get('draws', {}).get('total', '0')}
❌ Derrotas: {resumo.get('loses', {}).get('total', '0')}
⚽ Gols marcados: {gols.get('for', {}).get('total', {}).get('total', '0')}
🥅 Gols sofridos: {gols.get('against', {}).get('total', {}).get('total', '0')}
"""
    await update.message.reply_text(msg)

async def jogos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fixtures = get_data("fixtures", {"team": TEAM_ID, "season": SEASON, "league": LEAGUE_ID})
    if not fixtures:
        await update.message.reply_text("❌ Não encontrei jogos para a temporada 2023.")
        return

    resposta = "📋 Jogos do Bahia em 2023:\n\n"
    # Limita para não exceder o limite de mensagens do Telegram
    for jogo in fixtures[:15]:
        data = jogo.get("fixture", {}).get("date", "")[:10]
        # Determina o adversário
        times = jogo.get("teams", {})
        adversario = times.get("home", {}).get("name") if times.get("away", {}).get("id") == TEAM_ID else times.get("away", {}).get("name")
        # Determina o placar
        placar_mandante = jogo.get("goals", {}).get("home")
        placar_visitante = jogo.get("goals", {}).get("away")
        placar = f"{placar_mandante} - {placar_visitante}" if placar_mandante is not None else "Aguardando"
        
        resposta += f"{data} vs {adversario} → {placar}\n"

    await update.message.reply_text(resposta)

async def proximo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fixtures = get_data("fixtures", {"team": TEAM_ID, "season": SEASON, "league": LEAGUE_ID})
    if not fixtures:
        await update.message.reply_text("❌ Não encontrei jogos. A temporada pode ter sido finalizada.")
        return

    agora = datetime.datetime.now(datetime.timezone.utc)
    
    proximo_jogo = None
    for jogo in fixtures:
        data_jogo_str = jogo.get("fixture", {}).get("date")
        if data_jogo_str:
            data_jogo = datetime.datetime.fromisoformat(data_jogo_str.replace("Z", "+00:00"))
            if data_jogo > agora:
                proximo_jogo = jogo
                break

    if proximo_jogo:
        adversario = (proximo_jogo.get("teams", {}).get("home", {}).get("name") 
                      if proximo_jogo.get("teams", {}).get("away", {}).get("id") == TEAM_ID 
                      else proximo_jogo.get("teams", {}).get("away", {}).get("name"))
        data_formatada = data_jogo.strftime('%d/%m/%Y %H:%M')
        await update.message.reply_text(f"📅 Próximo jogo:\n{data_formatada}\nContra: {adversario}")
    else:
        await update.message.reply_text("✅ Não há próximos jogos (temporada finalizada).")

async def vitorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fixtures = get_data("fixtures", {"team": TEAM_ID, "season": SEASON, "league": LEAGUE_ID})
    if not fixtures:
        await update.message.reply_text("❌ Não consegui buscar jogos.")
        return

    vitorias_lista = []
    for jogo in fixtures:
        time_casa = jogo.get("teams", {}).get("home", {})
        time_fora = jogo.get("teams", {}).get("away", {})
        
        if time_casa.get("id") == TEAM_ID and time_casa.get("winner"):
            vitorias_lista.append(time_fora.get("name"))
        elif time_fora.get("id") == TEAM_ID and time_fora.get("winner"):
            vitorias_lista.append(time_casa.get("name"))

    if not vitorias_lista:
        await update.message.reply_text("❌ Não encontrei vitórias em 2023.")
    else:
        resposta = "✅ Times que o Bahia venceu em 2023:\n- " + "\n- ".join(sorted(list(set(vitorias_lista))))
        await update.message.reply_text(resposta)

async def artilheiro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = get_data("players", {"team": TEAM_ID, "season": SEASON})
    if not players:
        await update.message.reply_text("❌ Não consegui buscar jogadores.")
        return

    top_player = max(players, key=lambda p: p.get("statistics", [{}])[0].get("goals", {}).get("total") or 0)
    nome = top_player.get("player", {}).get("name")
    gols = top_player.get("statistics", [{}])[0].get("goals", {}).get("total")

    if nome and gols:
        await update.message.reply_text(f"⚽ Artilheiro do Bahia em {SEASON}: {nome} ({gols} gols)")
    else:
        await update.message.reply_text("❌ Não foi possível encontrar o artilheiro.")

async def assistencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = get_data("players", {"team": TEAM_ID, "season": SEASON})
    if not players:
        await update.message.reply_text("❌ Não consegui buscar jogadores.")
        return

    top_player = max(players, key=lambda p: p.get("statistics", [{}])[0].get("goals", {}).get("assists") or 0)
    nome = top_player.get("player", {}).get("name")
    assistencias = top_player.get("statistics", [{}])[0].get("goals", {}).get("assists")

    if nome and assistencias:
        await update.message.reply_text(f"🎯 Líder de assistências do Bahia em {SEASON}: {nome} ({assistencias} assistências)")
    else:
        await update.message.reply_text("❌ Não foi possível encontrar o líder de assistências.")

# =========================
# INICIALIZAÇÃO
# =========================
def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("estatisticas", estatisticas))
    app.add_handler(CommandHandler("vitorias", vitorias))
    app.add_handler(CommandHandler("artilheiro", artilheiro))
    app.add_handler(CommandHandler("assistencias", assistencias))
    app.add_handler(CommandHandler("jogos", jogos))
    app.add_handler(CommandHandler("proximo", proximo))

    PORT = int(os.environ.get("PORT", 10000))
    URL = os.environ.get("RENDER_EXTERNAL_URL")

    print("✅ Bot rodando com Webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()