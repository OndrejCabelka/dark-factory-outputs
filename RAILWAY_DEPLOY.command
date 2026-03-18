#!/bin/zsh
# Dark Factory — Railway Deploy
# Dvojklik na tento soubor ho spustí v Terminalu

cd /Users/ondrejcabelka/Desktop/DarkFactory

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   DARK FACTORY — RAILWAY DEPLOY      ║"
echo "╚══════════════════════════════════════╝"
echo ""

echo "▶ KROK 1: Login do Railway (otevře browser)..."
railway login

echo ""
echo "▶ KROK 2: Inicializace projektu..."
railway init --name DarkFactory

echo ""
echo "▶ KROK 3: Nastavování env proměnných..."
railway variables set \
  ANTHROPIC_API_KEY="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" \
  SERPER_API_KEY="61bb4c6106e446bf2a8204c32753952fe8054662" \
  BRAVE_API_KEY="BSAVlXGMLmsAThRGZ0_C64Ncz4mhhk_" \
  GITHUB_PERSONAL_ACCESS_TOKEN="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" \
  GITHUB_REPO="ondrejcabelka/dark-factory-outputs" \
  GUMROAD_ACCESS_TOKEN="XcW_WV5lnHS-PsYJBm3zDyu4Pg33BBh5aRKp_Iq-Woc" \
  GMAIL_ADDRESS="ondrej.cabelka@gmail.com" \
  RUN_ON_STARTUP="false"

echo ""
echo "▶ KROK 4: Deploy na Railway..."
railway up --detach

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  🚀 HOTOVO! Dark Factory běží 24/7!          ║"
echo "║  Výstupy: github.com/ondrejcabelka/          ║"
echo "║           dark-factory-outputs               ║"  
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Stiskni Enter pro zavření..."
read
