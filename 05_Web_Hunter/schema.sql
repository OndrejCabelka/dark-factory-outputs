-- WebHunter — Supabase schema
-- Spusť jednou v: https://supabase.com → SQL Editor

-- ──────────────────────────────────────────────
-- Tabulka: leads
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    obor             TEXT,
    mesto            TEXT,
    telefon          TEXT,
    email            TEXT,

    -- Web status
    web_status       TEXT CHECK (web_status IN ('bez_webu','jen_social','spatny_web')) DEFAULT 'bez_webu',
    web_url          TEXT,
    web_issues       TEXT[] DEFAULT '{}',

    -- Priorita: 1 = bez webu, 2 = jen social, 3 = špatný web
    priority         INTEGER DEFAULT 1,

    -- Workflow stav
    stav TEXT CHECK (stav IN (
        'novy',
        'navrh_vygenerovan',
        'ceka_na_hovor',
        'hovor_proveden',
        'souhlas_k_mailu',
        'odmitl',
        'nedostupny',
        'mail_odeslan',
        'otevrel_mail',
        'navrh_odeslan',
        'zakaznik',
        'neodpovida'
    )) DEFAULT 'novy',

    -- Volání
    call_note        TEXT,
    call_attempt     INTEGER DEFAULT 0,

    -- Deduplikace
    google_place_id  TEXT UNIQUE,
    tracking_id      TEXT UNIQUE,

    -- Timestampy
    mail_odeslan_at  TIMESTAMPTZ,
    mail_otevren_at  TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────
-- Tabulka: web_navrhy
-- HTML návrhy generované Claudem
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS web_navrhy (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id    UUID REFERENCES leads(id) ON DELETE CASCADE,
    html       TEXT NOT NULL,
    slug       TEXT UNIQUE NOT NULL,
    url        TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────
-- Tabulka: mail_log
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mail_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id     UUID REFERENCES leads(id) ON DELETE CASCADE,
    tracking_id TEXT,
    subject     TEXT,
    sent_at     TIMESTAMPTZ DEFAULT NOW(),
    opened_at   TIMESTAMPTZ,
    clicked_at  TIMESTAMPTZ
);

-- ──────────────────────────────────────────────
-- Automatický updated_at trigger
-- ──────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS leads_updated_at ON leads;
CREATE TRIGGER leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ──────────────────────────────────────────────
-- Indexy pro rychlé queries v dashboardu
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_leads_stav       ON leads(stav);
CREATE INDEX IF NOT EXISTS idx_leads_priority   ON leads(priority);
CREATE INDEX IF NOT EXISTS idx_leads_mesto      ON leads(mesto);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);

-- ──────────────────────────────────────────────
-- RLS — Row Level Security (volitelné)
-- Pokud chceš veřejné čtení pro dashboard:
-- ──────────────────────────────────────────────
-- ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "anon read" ON leads FOR SELECT USING (true);
-- CREATE POLICY "service write" ON leads FOR ALL USING (auth.role() = 'service_role');
