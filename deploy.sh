#!/bin/zsh
# Dark Factory — Railway deploy script
# Run this ONCE to get it live on Railway.
# After that it runs 24/7 automatically.

set -e

BASE="/Users/ondrejcabelka/Desktop/DarkFactory"
ENV_FILE="$BASE/_config/.env"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   DARK FACTORY — RAILWAY DEPLOY      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Load env vars
source "$ENV_FILE" 2>/dev/null || true

# Step 1: Railway login
echo "▶ STEP 1: Logging into Railway (browser will open)..."
railway login
echo "✅ Logged in"

# Step 2: Link or create project
echo ""
echo "▶ STEP 2: Creating Railway project..."
cd "$BASE"
railway init --name "dark-factory"
echo "✅ Project created"

# Step 3: Set environment variables on Railway
echo ""
echo "▶ STEP 3: Setting API keys on Railway..."
railway variables set \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  SERPER_API_KEY="$SERPER_API_KEY" \
  BRAVE_API_KEY="$BRAVE_API_KEY" \
  GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
  GITHUB_REPO="$GITHUB_REPO" \
  GMAIL_ADDRESS="$GMAIL_ADDRESS" \
  LANGCHAIN_API_KEY="$ANTHROPIC_API_KEY" \
  LANGCHAIN_TRACING_V2="true" \
  LANGCHAIN_PROJECT="DarkFactory" \
  RUN_ON_STARTUP="true"
echo "✅ Environment variables set"

# Step 4: Deploy
echo ""
echo "▶ STEP 4: Deploying to Railway..."
railway up --detach
echo "✅ Deployed!"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      DARK FACTORY — LIVE 24/7 ✅     ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Výsledky uvidíš na:"
echo "  👉 https://github.com/OndrejCabelka/dark-factory-outputs"
echo ""
echo "Každý den v 8-10h ráno factory automaticky:"
echo "  08:00 → Digital Products"
echo "  09:00 → Web Hunter"
echo "  10:00 → YouTube"
echo ""
echo "Logy na Railway: railway logs"
echo ""
