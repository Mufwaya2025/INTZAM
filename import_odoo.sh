#!/usr/bin/env bash
# =============================================================================
#  import_odoo.sh
#  IntZam Microfinance — Odoo 17 Import Script (SERVER SIDE)
#
#  Extracts an odoo_export_*.zip produced by export_odoo.sh and restores
#  the database, filestore, custom module, and config on the target server.
#
#  Prerequisites on the production server
#  ───────────────────────────────────────
#  • Odoo 17 Community installed at /opt/odoo17  (same layout as source)
#  • PostgreSQL 16 running
#  • A PostgreSQL superuser or a user that can CREATE DATABASE
#  • The zip archive already transferred to the server
#
#  Usage
#  ─────
#  bash import_odoo.sh --archive /opt/odoo_imports/odoo_export_20260314.zip
#  bash import_odoo.sh --archive <file> --target-db lms_production
#  bash import_odoo.sh --archive <file> --target-db lms_production --dry-run
#
#  Flags
#  ─────
#  --archive    <path>   Path to the .zip file  (required)
#  --target-db  <name>   Target database name   (default: odoo_lms_production)
#  --db-user    <name>   PostgreSQL user        (default: odoo_user)
#  --odoo-user  <name>   OS user Odoo runs as   (default: odoo)
#  --dry-run             Show what would happen, don't execute
#  --skip-db             Skip database restore (filestore + module only)
#  --skip-filestore      Skip filestore restore
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()    { echo -e "  ${GREEN}✓${RESET} $*"; }
warn()  { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
err()   { echo -e "  ${RED}✗${RESET} $*" >&2; }
step()  { echo -e "\n${CYAN}${BOLD}── $* ${RESET}"; }
dryrun(){ echo -e "  ${YELLOW}[DRY RUN]${RESET} $*"; }

# ── Defaults ──────────────────────────────────────────────────────────────────
ARCHIVE=""
TARGET_DB="odoo_lms_production"
DB_USER="odoo_user"
DB_HOST="localhost"
DB_PORT="5432"
ODOO_OS_USER="odoo"
ODOO_CONF_DEST="/etc/odoo17.conf"
ODOO_HOME="/opt/odoo17"
CUSTOM_ADDONS_DEST="/opt/odoo17/custom_addons"
FILESTORE_BASE=""   # auto-detected from conf or defaulted
DRY_RUN=0
SKIP_DB=0
SKIP_FILESTORE=0
ODOO_SERVICE="odoo17"   # systemd unit name — adjust if different

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive)       ARCHIVE="$2";      shift 2 ;;
    --target-db)     TARGET_DB="$2";    shift 2 ;;
    --db-user)       DB_USER="$2";      shift 2 ;;
    --odoo-user)     ODOO_OS_USER="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=1;         shift ;;
    --skip-db)       SKIP_DB=1;         shift ;;
    --skip-filestore) SKIP_FILESTORE=1; shift ;;
    --help|-h)
      grep '^#  ' "$0" | sed 's/^#  //'
      exit 0 ;;
    *) err "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$ARCHIVE" ]]; then
  err "Required: --archive <path-to-zip>"
  echo "Usage: bash import_odoo.sh --archive /path/to/odoo_export_*.zip"
  exit 1
fi
if [[ ! -f "$ARCHIVE" ]]; then
  err "Archive not found: $ARCHIVE"
  exit 1
fi

# ── Work directory ────────────────────────────────────────────────────────────
WORK_DIR="$(mktemp -d /tmp/odoo_import_XXXXXX)"
trap 'echo -e "\n${YELLOW}Cleaning up temp directory...${RESET}"; rm -rf "$WORK_DIR"' EXIT

# ── Helper: run or dry-run ────────────────────────────────────────────────────
run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    dryrun "$@"
  else
    "$@"
  fi
}

# =============================================================================
echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
echo -e   "║   IntZam Odoo 17 — Import Script             ║"
echo -e   "╚══════════════════════════════════════════════╝${RESET}"
echo -e   "  Archive   : ${BOLD}$(basename "$ARCHIVE")${RESET}"
echo -e   "  Target DB : ${BOLD}$TARGET_DB${RESET}"
echo -e   "  DB User   : ${BOLD}$DB_USER${RESET}"
[[ "$DRY_RUN" -eq 1 ]] && echo -e "  ${YELLOW}${BOLD}DRY RUN MODE — nothing will be changed${RESET}"

# ── Preflight checks ──────────────────────────────────────────────────────────
step "Preflight checks"

for cmd in psql pg_isready rsync; do
  if command -v "$cmd" &>/dev/null; then
    ok "$cmd available"
  else
    err "$cmd not found. Install: sudo apt install postgresql-client rsync"
    exit 1
  fi
done

# unzip is optional — fall back to python3 if not installed
if command -v unzip &>/dev/null; then
  UNZIP_CMD="system"
  ok "unzip available"
elif command -v python3 &>/dev/null; then
  UNZIP_CMD="python3"
  ok "unzip not found — will use python3 zipfile module"
else
  err "Neither 'unzip' nor 'python3' is available. Install: sudo apt install unzip"
  exit 1
fi

if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" &>/dev/null; then
  ok "PostgreSQL reachable ($DB_HOST:$DB_PORT)"
else
  err "PostgreSQL not ready. Start it: sudo systemctl start postgresql"
  exit 1
fi

if [[ ! -d "$ODOO_HOME" ]]; then
  err "Odoo not found at $ODOO_HOME. Install Odoo 17 first."
  exit 1
fi
ok "Odoo installation: $ODOO_HOME"

# Warn if Odoo is still running
if systemctl is-active --quiet "$ODOO_SERVICE" 2>/dev/null; then
  warn "Odoo service '$ODOO_SERVICE' is RUNNING."
  warn "Importing while Odoo is running can corrupt the filestore."
  read -rp "  Stop it now? [Y/n]: " STOP_ODOO
  STOP_ODOO="${STOP_ODOO:-Y}"
  if [[ "${STOP_ODOO^^}" == "Y" ]]; then
    run sudo systemctl stop "$ODOO_SERVICE"
    ok "Odoo service stopped"
  else
    warn "Continuing with Odoo running — proceed at your own risk."
  fi
else
  ok "Odoo service is not running (safe to import)"
fi

# ── Extract archive ───────────────────────────────────────────────────────────
step "Extracting archive"

ARCHIVE_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
ok "Archive: $(basename "$ARCHIVE") ($ARCHIVE_SIZE)"

if [[ "$UNZIP_CMD" == "system" ]]; then
  unzip -q "$ARCHIVE" -d "$WORK_DIR"
else
  python3 -c "
import zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as zf:
    zf.extractall(sys.argv[2])
" "$ARCHIVE" "$WORK_DIR"
fi
ok "Extracted to: $WORK_DIR"

# Verify manifest
if [[ -f "$WORK_DIR/MANIFEST.txt" ]]; then
  ok "Manifest found:"
  grep -E "^  (Export timestamp|Odoo version|Source DB)" "$WORK_DIR/MANIFEST.txt" \
    | sed 's/^/    /' || true
else
  warn "No MANIFEST.txt found — archive may be from a different tool."
fi

# Locate the SQL dump
SQL_FILE=$(find "$WORK_DIR" -maxdepth 1 -name "database_*.sql" | head -1)
if [[ -z "$SQL_FILE" && "$SKIP_DB" -eq 0 ]]; then
  err "No SQL dump found in archive. Contents: $(ls "$WORK_DIR")"
  exit 1
fi
[[ -n "$SQL_FILE" ]] && ok "SQL dump: $(basename "$SQL_FILE") ($(du -sh "$SQL_FILE" | cut -f1))"

# Locate filestore
EXTRACTED_FILESTORE=$(find "$WORK_DIR/filestore" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)
SOURCE_DB_NAME=$(basename "$EXTRACTED_FILESTORE" 2>/dev/null || echo "")

# ── Step 1: Database restore ──────────────────────────────────────────────────
if [[ "$SKIP_DB" -eq 1 ]]; then
  warn "Skipping database restore (--skip-db)"
else
  step "Step 1/4 — Restoring database: $TARGET_DB"

  # Check if target DB already exists
  if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
          -lqt 2>/dev/null | cut -d'|' -f1 | grep -qw "$TARGET_DB"; then
    warn "Database '$TARGET_DB' already exists."
    read -rp "  Drop and recreate it? Data will be lost. [y/N]: " CONFIRM_DROP
    if [[ "${CONFIRM_DROP^^}" == "Y" ]]; then
      run psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
          -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$TARGET_DB';" \
          postgres
      run psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
          -c "DROP DATABASE IF EXISTS \"$TARGET_DB\";" postgres
      ok "Dropped existing database"
    else
      warn "Keeping existing database — SQL will be applied on top (may fail on conflicts)."
    fi
  fi

  # Create database if it doesn't exist now
  if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
          -lqt 2>/dev/null | cut -d'|' -f1 | grep -qw "$TARGET_DB"; then
    run psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -c "CREATE DATABASE \"$TARGET_DB\" OWNER \"$DB_USER\";" postgres
    ok "Created database: $TARGET_DB"
  fi

  # Restore the dump
  echo -e "  Restoring SQL dump (this may take a few minutes)..."
  run psql \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$TARGET_DB" \
    --quiet \
    --file="$SQL_FILE" 2>&1 | grep -v "^$" || true

  ok "SQL dump restored into '$TARGET_DB'"

  # If source DB name differs from target, update the internal Odoo DB references
  if [[ -n "$SOURCE_DB_NAME" && "$SOURCE_DB_NAME" != "$TARGET_DB" ]]; then
    warn "Source DB was '$SOURCE_DB_NAME', target is '$TARGET_DB'."
    warn "Updating ir.config_parameter 'web.base.url.static' if needed..."
    run psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -d "$TARGET_DB" \
        -c "UPDATE ir_config_parameter SET value = replace(value, '$SOURCE_DB_NAME', '$TARGET_DB') WHERE key LIKE '%db%';" \
        2>/dev/null || true
  fi
fi

# ── Step 2: Filestore ─────────────────────────────────────────────────────────
if [[ "$SKIP_FILESTORE" -eq 1 ]]; then
  warn "Skipping filestore restore (--skip-filestore)"
elif [[ -z "$EXTRACTED_FILESTORE" ]]; then
  warn "No filestore found in archive — skipping"
else
  step "Step 2/4 — Restoring filestore"

  # Auto-detect data_dir from config file
  if [[ -f "$ODOO_CONF_DEST" ]]; then
    DATA_DIR=$(grep -E "^\s*data_dir\s*=" "$ODOO_CONF_DEST" \
               | head -1 | sed 's/.*=\s*//' | tr -d ' \r')
  else
    DATA_DIR="/home/$ODOO_OS_USER/.local/share/Odoo"
  fi
  FILESTORE_DEST="$DATA_DIR/filestore/$TARGET_DB"

  run sudo mkdir -p "$FILESTORE_DEST"
  run sudo rsync -a --info=progress2 --delete \
      "$EXTRACTED_FILESTORE/" "$FILESTORE_DEST/"
  run sudo chown -R "$ODOO_OS_USER:$ODOO_OS_USER" "$DATA_DIR/filestore/" 2>/dev/null || true
  ok "Filestore restored → $FILESTORE_DEST"
fi

# ── Step 3: lms_bridge module ─────────────────────────────────────────────────
step "Step 3/4 — Installing lms_bridge module"

EXTRACTED_BRIDGE="$WORK_DIR/custom_addons/lms_bridge"
if [[ -d "$EXTRACTED_BRIDGE" ]]; then
  run sudo mkdir -p "$CUSTOM_ADDONS_DEST"
  run sudo rsync -a --delete --exclude='__pycache__' --exclude='*.pyc' \
      "$EXTRACTED_BRIDGE" "$CUSTOM_ADDONS_DEST/"
  run sudo chown -R "$ODOO_OS_USER:$ODOO_OS_USER" "$CUSTOM_ADDONS_DEST/lms_bridge/" 2>/dev/null || true
  ok "lms_bridge copied → $CUSTOM_ADDONS_DEST/lms_bridge/"

  # Show module version
  if [[ -f "$EXTRACTED_BRIDGE/__manifest__.py" ]]; then
    VERSION=$(grep '"version"' "$EXTRACTED_BRIDGE/__manifest__.py" | head -1 | sed 's/.*: *"\(.*\)".*/\1/')
    ok "lms_bridge version: $VERSION"
  fi
else
  warn "lms_bridge directory not found in archive — skipping"
fi

# ── Step 4: Odoo configuration ────────────────────────────────────────────────
step "Step 4/4 — Installing Odoo configuration"

EXTRACTED_CONF="$WORK_DIR/odoo17.conf"
if [[ -f "$EXTRACTED_CONF" ]]; then
  # Make a backup of any existing config
  if [[ -f "$ODOO_CONF_DEST" ]]; then
    BACKUP="${ODOO_CONF_DEST}.bak.$(date +%Y%m%d_%H%M%S)"
    run sudo cp "$ODOO_CONF_DEST" "$BACKUP"
    ok "Existing config backed up → $BACKUP"
  fi

  run sudo cp "$EXTRACTED_CONF" "$ODOO_CONF_DEST"
  run sudo chown root:root "$ODOO_CONF_DEST"
  run sudo chmod 640 "$ODOO_CONF_DEST"
  ok "Config installed → $ODOO_CONF_DEST"

  warn "IMPORTANT: Edit $ODOO_CONF_DEST and update:"
  warn "  • db_name     → $TARGET_DB"
  warn "  • db_password → production DB password"
  warn "  • admin_passwd → change from test value"
  warn "  • workers     → set based on server CPU count"
  warn "  • logfile     → ensure /var/log/odoo17/ exists and is writable"
  warn "  • data_dir    → confirm /home/odoo/.local/share/Odoo or similar"
else
  warn "No odoo17.conf found in archive — skipping"
fi

# ── Update lms_bridge in target database ─────────────────────────────────────
step "Updating lms_bridge in Odoo database"

if [[ "$DRY_RUN" -eq 1 ]]; then
  dryrun "Would run: sudo -u $ODOO_OS_USER $ODOO_HOME/venv/bin/python $ODOO_HOME/odoo-bin -u lms_bridge ..."
elif [[ -d "$CUSTOM_ADDONS_DEST/lms_bridge" ]]; then
  echo "  Running Odoo module update (lms_bridge)..."
  sudo -u "$ODOO_OS_USER" "$ODOO_HOME/venv/bin/python" "$ODOO_HOME/odoo-bin" \
    --config="$ODOO_CONF_DEST" \
    --database="$TARGET_DB" \
    --update=lms_bridge \
    --stop-after-init \
    2>&1 | tail -5
  ok "lms_bridge updated in database '$TARGET_DB'"
fi

# ── Summary and post-import checklist ────────────────────────────────────────
echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
echo -e   "║   Import complete — Post-import checklist     ║"
echo -e   "╚══════════════════════════════════════════════╝${RESET}"

cat << CHECKLIST

  Configuration (MUST do before starting Odoo)
  ─────────────────────────────────────────────
  [ ] Edit $ODOO_CONF_DEST:
        db_name     = $TARGET_DB
        db_password = <production password>
        admin_passwd = <new master password>
        workers     = <CPU count - 1>  (e.g. 3 for a 4-core server)
        logfile     = /var/log/odoo17/odoo.log
        data_dir    = /home/$ODOO_OS_USER/.local/share/Odoo

  [ ] Ensure log directory exists:
        sudo mkdir -p /var/log/odoo17
        sudo chown $ODOO_OS_USER:$ODOO_OS_USER /var/log/odoo17

  [ ] Update web.base.url in Odoo DB to production URL:
        psql -U $DB_USER -d $TARGET_DB -c \\
          "UPDATE ir_config_parameter SET value='https://YOUR_DOMAIN' \\
           WHERE key='web.base.url';"

  Start and verify Odoo
  ──────────────────────
  [ ] Start Odoo:
        sudo systemctl start $ODOO_SERVICE

  [ ] Tail the log for errors:
        sudo tail -50f /var/log/odoo17/odoo.log

  [ ] Open the Odoo UI in a browser and log in.

  Odoo UI verification
  ──────────────────────
  [ ] Settings → Company: name, country=Zambia, currency=ZMW
  [ ] Accounting → Configuration → Journals:
        LDIS, LRPY, LINT, LFEE, LPROV all present
  [ ] Apps → Installed: lms_bridge shows version 17.0.1.0.0
  [ ] LMS Bridge → Loan Events: menu accessible

  LMS Django backend
  ──────────────────
  [ ] Update backend/.env.production:
        ODOO_URL      = http://YOUR_SERVER:8069
        ODOO_DB       = $TARGET_DB
        ODOO_USER     = <service account — NOT admin>
        ODOO_PASSWORD = <service account password>
  [ ] Run the connection test:
        APP_ENV=production python manage.py shell -c \\
          "from apps.accounting.odoo_client import get_odoo_client; \\
           print(get_odoo_client().ping())"

  Security
  ─────────
  [ ] Create a dedicated Odoo service user (not admin):
        In Odoo: Settings → Users → New
        Role: Accounting / Billing + Technical Features
  [ ] Revoke public DB access if PostgreSQL is exposed:
        sudo -u postgres psql -c "REVOKE CONNECT ON DATABASE $TARGET_DB FROM PUBLIC;"
  [ ] Set file permissions on config:
        sudo chmod 640 $ODOO_CONF_DEST

CHECKLIST

echo -e "  Import archive: ${BOLD}$(basename "$ARCHIVE")${RESET}"
[[ "$DRY_RUN" -eq 1 ]] && echo -e "  ${YELLOW}DRY RUN — no changes were made to the system.${RESET}"
echo ""
