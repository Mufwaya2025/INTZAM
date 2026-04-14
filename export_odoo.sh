#!/usr/bin/env bash
# =============================================================================
#  export_odoo.sh
#  IntZam Microfinance — Odoo 17 Export Script
#
#  Packages the local WSL test environment into a single dated zip archive
#  ready to be transferred to the production server.
#
#  What it captures
#  ─────────────────
#  1. PostgreSQL dump of odoo_lms_test  (full schema + data)
#  2. Odoo filestore                    (~/.local/share/Odoo/filestore/<db>)
#  3. lms_bridge custom module          (/opt/odoo17/custom_addons/lms_bridge)
#  4. Odoo server config                (/etc/odoo17.conf)
#  5. Manifest                          (versions, checksums, timestamps)
#
#  Usage
#  ─────
#  bash export_odoo.sh
#  bash export_odoo.sh --db-name my_other_db   # override database name
#  bash export_odoo.sh --output-dir /tmp        # change output directory
#
#  Output
#  ─────
#  ~/odoo_exports/odoo_export_YYYYMMDD_HHMMSS.zip
# =============================================================================

set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET} $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
err()  { echo -e "  ${RED}✗${RESET} $*" >&2; }
step() { echo -e "\n${CYAN}${BOLD}── $* ${RESET}"; }

# ── Defaults (override via flags) ─────────────────────────────────────────────
DB_NAME="odoo_lms_test"
DB_USER="odoo_user"
DB_HOST="localhost"
DB_PORT="5432"
ODOO_CONF="/etc/odoo17.conf"
FILESTORE_BASE="$HOME/.local/share/Odoo/filestore"
CUSTOM_ADDONS_DIR="/opt/odoo17/custom_addons/lms_bridge"
OUTPUT_DIR="$HOME/odoo_exports"

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-name)     DB_NAME="$2";    shift 2 ;;
    --db-user)     DB_USER="$2";    shift 2 ;;
    --output-dir)  OUTPUT_DIR="$2"; shift 2 ;;
    --help|-h)
      grep '^#  ' "$0" | sed 's/^#  //'
      exit 0 ;;
    *) err "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Derived paths ─────────────────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATESTAMP=$(date +%Y%m%d)
ARCHIVE_NAME="odoo_export_${DATESTAMP}.zip"
WORK_DIR="$(mktemp -d /tmp/odoo_export_XXXXXX)"
FILESTORE_PATH="$FILESTORE_BASE/$DB_NAME"

# ── Cleanup on exit ───────────────────────────────────────────────────────────
trap 'echo -e "\n${YELLOW}Cleaning up temp directory...${RESET}"; rm -rf "$WORK_DIR"' EXIT

# =============================================================================
echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
echo -e   "║   IntZam Odoo 17 — Export Script             ║"
echo -e   "╚══════════════════════════════════════════════╝${RESET}"
echo -e   "  Database : ${BOLD}$DB_NAME${RESET}"
echo -e   "  Timestamp: ${BOLD}$TIMESTAMP${RESET}"
echo -e   "  Output   : ${BOLD}$OUTPUT_DIR/$ARCHIVE_NAME${RESET}"

# ── Preflight checks ──────────────────────────────────────────────────────────
step "Preflight checks"

for cmd in pg_dump rsync; do
  if command -v "$cmd" &>/dev/null; then
    ok "$cmd found ($(command -v $cmd))"
  else
    err "$cmd not found. Install with: sudo apt install $cmd"
    exit 1
  fi
done

# zip is optional — fall back to python3 -m zipfile if not installed
if command -v zip &>/dev/null; then
  ZIP_CMD="system"
  ok "zip found ($(command -v zip))"
elif command -v python3 &>/dev/null; then
  ZIP_CMD="python3"
  ok "zip not found — will use python3 zipfile module (always available)"
else
  err "Neither 'zip' nor 'python3' is available. Install zip: sudo apt install zip"
  exit 1
fi

if [[ ! -f "$ODOO_CONF" ]]; then
  err "Odoo config not found: $ODOO_CONF"
  exit 1
fi
ok "Odoo config: $ODOO_CONF"

if [[ ! -d "$FILESTORE_PATH" ]]; then
  warn "Filestore not found at $FILESTORE_PATH — will skip"
  SKIP_FILESTORE=1
else
  ok "Filestore: $FILESTORE_PATH ($(du -sh "$FILESTORE_PATH" | cut -f1))"
  SKIP_FILESTORE=0
fi

if [[ ! -d "$CUSTOM_ADDONS_DIR" ]]; then
  err "lms_bridge not found: $CUSTOM_ADDONS_DIR"
  exit 1
fi
ok "lms_bridge: $CUSTOM_ADDONS_DIR"

# Check PostgreSQL is reachable
if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" &>/dev/null; then
  ok "PostgreSQL is running ($DB_HOST:$DB_PORT)"
else
  err "PostgreSQL not ready at $DB_HOST:$DB_PORT. Start it first."
  exit 1
fi

# Check database exists
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -lqt 2>/dev/null | cut -d'|' -f1 | grep -qw "$DB_NAME"; then
  ok "Database '$DB_NAME' exists"
else
  err "Database '$DB_NAME' not found. Check --db-name."
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

# ── Step 1: PostgreSQL dump ───────────────────────────────────────────────────
step "Step 1/5 — Dumping PostgreSQL database"

SQL_FILE="$WORK_DIR/database_${DB_NAME}_${TIMESTAMP}.sql"
pg_dump \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --username="$DB_USER" \
  --format=plain \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  --file="$SQL_FILE" \
  "$DB_NAME"

SQL_SIZE=$(du -sh "$SQL_FILE" | cut -f1)
ok "Database dumped → $(basename "$SQL_FILE") ($SQL_SIZE)"

# ── Step 2: Filestore ─────────────────────────────────────────────────────────
step "Step 2/5 — Copying Odoo filestore"

if [[ "${SKIP_FILESTORE:-0}" -eq 0 ]]; then
  FILESTORE_DEST="$WORK_DIR/filestore/$DB_NAME"
  mkdir -p "$FILESTORE_DEST"
  rsync -a --info=progress2 "$FILESTORE_PATH/" "$FILESTORE_DEST/"
  FS_SIZE=$(du -sh "$FILESTORE_DEST" | cut -f1)
  ok "Filestore copied → filestore/$DB_NAME/ ($FS_SIZE)"
else
  warn "Filestore skipped (directory not found)"
fi

# ── Step 3: lms_bridge custom module ──────────────────────────────────────────
step "Step 3/5 — Copying lms_bridge module"

ADDONS_DEST="$WORK_DIR/custom_addons"
mkdir -p "$ADDONS_DEST"
rsync -a --exclude='__pycache__' --exclude='*.pyc' \
  "$CUSTOM_ADDONS_DIR" "$ADDONS_DEST/"
ok "lms_bridge copied → custom_addons/lms_bridge/"

# ── Step 4: Odoo configuration ────────────────────────────────────────────────
step "Step 4/5 — Copying Odoo config"

cp "$ODOO_CONF" "$WORK_DIR/odoo17.conf"
ok "Config copied → odoo17.conf"

# ── Step 5: Manifest ──────────────────────────────────────────────────────────
step "Step 5/5 — Writing manifest"

ODOO_VERSION=$(/opt/odoo17/venv/bin/python \
  /opt/odoo17/odoo-bin --version 2>/dev/null \
  | head -1 || echo "unknown")

cat > "$WORK_DIR/MANIFEST.txt" << MANIFEST
═══════════════════════════════════════════════════════════════
  IntZam Microfinance — Odoo 17 Export Manifest
═══════════════════════════════════════════════════════════════

Export timestamp : $TIMESTAMP
Exported by      : $(whoami)@$(hostname)
Odoo version     : $ODOO_VERSION
PostgreSQL dump  : $(pg_dump --version | head -1)

Contents
────────
  database_${DB_NAME}_${TIMESTAMP}.sql   Full schema + data dump
  filestore/$DB_NAME/                     Odoo binary attachments
  custom_addons/lms_bridge/               LMS Bridge custom module
  odoo17.conf                             Server configuration

Database
────────
  Source DB name  : $DB_NAME
  Source DB user  : $DB_USER
  Source host     : $DB_HOST:$DB_PORT
  Dump format     : plain SQL (--format=plain)
  Flags           : --no-owner --no-acl --clean --if-exists

lms_bridge version
──────────────────
$(grep '"version"' "$CUSTOM_ADDONS_DIR/__manifest__.py" 2>/dev/null || echo "  see __manifest__.py")

Checksums (SHA-256)
───────────────────
$(sha256sum "$WORK_DIR/database_${DB_NAME}_${TIMESTAMP}.sql" | awk '{print "  "$1"  database_'${DB_NAME}'_'${TIMESTAMP}'.sql"}')
$(sha256sum "$WORK_DIR/odoo17.conf" | awk '{print "  "$1"  odoo17.conf"}')

Import instructions
───────────────────
  See IMPORT_CHECKLIST.txt or run import_odoo.sh on the target server.

═══════════════════════════════════════════════════════════════
MANIFEST

ok "Manifest written → MANIFEST.txt"

# ── Zip everything ────────────────────────────────────────────────────────────
step "Zipping archive"

ARCHIVE_PATH="$OUTPUT_DIR/$ARCHIVE_NAME"

if [[ "$ZIP_CMD" == "system" ]]; then
  (cd "$WORK_DIR" && zip -r "$ARCHIVE_PATH" . -x "*.DS_Store")
  zip -T "$ARCHIVE_PATH" &>/dev/null && ok "Archive integrity verified (zip -T)" || {
    err "Archive failed integrity check!"
    exit 1
  }
else
  # Python fallback — creates an identical .zip file
  python3 - "$WORK_DIR" "$ARCHIVE_PATH" << 'PYZIPEOF'
import sys, zipfile, os
src_dir, dest_zip = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != '.DS_Store']
        for fname in files:
            fpath = os.path.join(root, fname)
            arcname = os.path.relpath(fpath, src_dir)
            zf.write(fpath, arcname)
print(f"  Created {dest_zip}")
PYZIPEOF
  # Verify readability
  python3 -c "import zipfile; zipfile.ZipFile('$ARCHIVE_PATH').testzip(); print('  Archive integrity OK')"
fi

ARCHIVE_SIZE=$(du -sh "$ARCHIVE_PATH" | cut -f1)
ok "Archive created → $ARCHIVE_PATH ($ARCHIVE_SIZE)"

# ── Post-export checklist ─────────────────────────────────────────────────────
echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
echo -e   "║   Export complete — Manual steps required    ║"
echo -e   "╚══════════════════════════════════════════════╝${RESET}"

cat << 'CHECKLIST'

  BEFORE transferring the archive
  ────────────────────────────────
  [ ] Check that Odoo is NOT actively processing journals — wait for any
      running cron jobs to finish to avoid a dirty dump.
  [ ] Note the Odoo master password (admin_passwd in odoo17.conf) —
      you will need it to restore the database via the Odoo UI if needed.

  Transferring to the server
  ──────────────────────────
  Run one of these from this machine:

  # Option A — SCP
  scp ~/odoo_exports/odoo_export_*.zip user@YOUR_SERVER:/opt/odoo_imports/

  # Option B — rsync (resumable)
  rsync -avP ~/odoo_exports/odoo_export_*.zip \
        user@YOUR_SERVER:/opt/odoo_imports/

  On the production server
  ─────────────────────────
  [ ] Stop the production Odoo service before importing:
        sudo systemctl stop odoo17

  [ ] Run import_odoo.sh (copy it to the server too):
        bash import_odoo.sh --archive /opt/odoo_imports/odoo_export_*.zip

  [ ] Review odoo17.conf — update db_password, admin_passwd, workers,
      logfile path, and any server-specific limits.

  [ ] Re-install lms_bridge on the production Odoo DB:
        cd /opt/odoo17
        sudo -u odoo ./venv/bin/python odoo-bin \
          --config=/etc/odoo17.conf \
          -u lms_bridge \
          --stop-after-init

  [ ] Update the LMS backend .env.production with the production Odoo
      URL, DB name, and service account credentials.

  [ ] Restart Odoo:
        sudo systemctl start odoo17

  [ ] Log into the production Odoo UI and verify:
        ✓ Company name / currency / country
        ✓ All 5 LMS journals present (LDIS, LRPY, LINT, LFEE, LPROV)
        ✓ lms_bridge module status = Installed
        ✓ LMS Bridge → Loan Events accessible

CHECKLIST

echo -e "  Archive: ${BOLD}$ARCHIVE_PATH${RESET}  (${ARCHIVE_SIZE})\n"
