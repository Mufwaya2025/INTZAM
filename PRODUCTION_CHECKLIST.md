# IntZam Microfinance — Production Deployment Checklist
**Odoo 17 Community + Python LMS → Ubuntu 22.04 Production Server**

> Run through every item in order. Tick each box before moving to the next.
> A missed step in section 3 will cause a silent failure in section 8.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Action to perform |
| `✓ Expected:` | What success looks like |
| `⚠ Watch out:` | Common failure point |
| `~N min` | Approximate time |

---

## Section 1 — Server Prerequisites `~15 min`

**Goal:** A clean Ubuntu 22.04 server that can run Odoo 17 and serve HTTPS traffic.

### 1.1 — Operating system

```
[ ] 1.  Provision Ubuntu 22.04 LTS (minimum: 2 vCPU, 4 GB RAM, 40 GB disk).
        Recommended for production: 4 vCPU, 8 GB RAM, 80 GB SSD.
```
✓ Expected: `lsb_release -rs` returns `22.04`

```
[ ] 2.  Update all packages.
        sudo apt update && sudo apt upgrade -y
```
✓ Expected: No errors; `uname -r` shows kernel ≥ 5.15

```
[ ] 3.  Create a dedicated OS user for Odoo (never run Odoo as root).
        sudo adduser --system --group --home /opt/odoo --shell /bin/bash odoo
```
✓ Expected: `id odoo` shows uid and gid

```
[ ] 4.  Open firewall ports: 22 (SSH), 80 (HTTP), 443 (HTTPS).
        Keep 8069 closed to the public — Nginx will proxy it.
        sudo ufw allow OpenSSH
        sudo ufw allow 'Nginx Full'
        sudo ufw enable
```
✓ Expected: `sudo ufw status` shows 80, 443, 22 ALLOW

### 1.2 — System dependencies

```
[ ] 5.  Install Odoo 17 system dependencies.
        sudo apt install -y \
          python3 python3-dev python3-pip python3-venv \
          build-essential libxml2-dev libxslt1-dev libsasl2-dev \
          libldap2-dev libssl-dev libjpeg-dev libpng-dev \
          libffi-dev zlib1g-dev libbz2-dev libreadline-dev \
          libpq-dev libcurl4-openssl-dev node-less npm git \
          wkhtmltopdf fontconfig xfonts-75dpi xfonts-base \
          postgresql postgresql-client nginx certbot python3-certbot-nginx
```
✓ Expected: All packages install without errors

```
[ ] 6.  Verify wkhtmltopdf produces PDFs (required for Odoo reports).
        wkhtmltopdf --version
```
✓ Expected: `wkhtmltopdf 0.12.x` (with patched Qt)

```
[ ] 7.  Verify Python version.
        python3 --version
```
✓ Expected: `Python 3.10.x` or higher

---

## Section 2 — PostgreSQL Restore `~10 min`

**Goal:** Production database running with correct permissions.

```
[ ] 8.  Start PostgreSQL and enable it on boot.
        sudo systemctl enable --now postgresql
```
✓ Expected: `sudo systemctl status postgresql` shows `active (running)`

```
[ ] 9.  Create the Odoo database user (use a strong password — NOT odoo_pass_2025).
        sudo -u postgres psql << 'SQL'
        CREATE USER odoo_user WITH PASSWORD 'CHANGE_ME_strong_password_here';
        ALTER USER odoo_user CREATEDB;
        SQL
```
✓ Expected: `CREATE ROLE` with no errors

⚠ Watch out: The user needs `CREATEDB` so Odoo can manage its own schema.
  Do NOT grant SUPERUSER in production.

```
[ ] 10. Transfer the export archive to the server.
        # From your WSL machine:
        scp ~/odoo_exports/odoo_export_*.zip user@YOUR_SERVER:/opt/odoo_imports/

        # On the server — create the imports directory first:
        sudo mkdir -p /opt/odoo_imports
```
✓ Expected: `ls /opt/odoo_imports/*.zip` shows the file

```
[ ] 11. Extract and restore the database using import_odoo.sh.
        sudo mkdir -p /opt/odoo_imports
        scp import_odoo.sh user@YOUR_SERVER:/opt/odoo_imports/
        bash /opt/odoo_imports/import_odoo.sh \
          --archive /opt/odoo_imports/odoo_export_*.zip \
          --target-db odoo_lms_production \
          --db-user odoo_user \
          --odoo-user odoo \
          --skip-db   # use this flag on first run, add DB manually below
```

```
[ ] 12. Create the production database and restore the SQL dump manually.
        sudo -u postgres createdb -O odoo_user odoo_lms_production
        psql -h localhost -U odoo_user -d odoo_lms_production \
             -f /tmp/odoo_import_*/database_odoo_lms_test_*.sql 2>&1 \
           | grep -v "^$" | tail -20
```
✓ Expected: Final lines show no FATAL errors; warnings about ownership are normal

```
[ ] 13. Verify the database has the lms_bridge tables.
        psql -h localhost -U odoo_user -d odoo_lms_production \
          -c "\dt lms_*"
```
✓ Expected: `lms_loan_event` table listed

```
[ ] 14. Update the base URL stored in the database.
        psql -h localhost -U odoo_user -d odoo_lms_production -c "
          UPDATE ir_config_parameter
          SET value = 'https://odoo.YOUR_DOMAIN.com'
          WHERE key = 'web.base.url';
        "
```
✓ Expected: `UPDATE 1`

---

## Section 3 — Odoo 17 Installation `~20 min`

**Goal:** Odoo 17 Community source code + venv matching the WSL setup.

```
[ ] 15. Clone Odoo 17 Community (same version as WSL — check with git log on WSL).
        sudo mkdir -p /opt/odoo17
        sudo chown odoo:odoo /opt/odoo17
        sudo -u odoo git clone https://github.com/odoo/odoo.git \
          --depth 1 --branch 17.0 /opt/odoo17
```
✓ Expected: `/opt/odoo17/odoo-bin` exists

⚠ Watch out: Use the same git branch/tag as WSL to avoid database upgrade mismatches.
  Check WSL: `cd /opt/odoo17 && git log --oneline -1`

```
[ ] 16. Create Python virtual environment and install dependencies.
        sudo -u odoo python3 -m venv /opt/odoo17/venv
        sudo -u odoo /opt/odoo17/venv/bin/pip install \
          --upgrade pip setuptools wheel
        # Pin setuptools to avoid pkg_resources removal in 82+
        sudo -u odoo /opt/odoo17/venv/bin/pip install "setuptools<81"
        sudo -u odoo /opt/odoo17/venv/bin/pip install \
          -r /opt/odoo17/requirements.txt
```
✓ Expected: No build errors; `pip list | grep odoo` (or similar) completes

⚠ Watch out: If `ldap` fails to build, install: `sudo apt install libsasl2-dev libldap2-dev`

```
[ ] 17. Copy the lms_bridge module from the archive.
        sudo mkdir -p /opt/odoo17/custom_addons
        sudo cp -r /tmp/odoo_import_*/custom_addons/lms_bridge \
          /opt/odoo17/custom_addons/
        sudo chown -R odoo:odoo /opt/odoo17/custom_addons/
```
✓ Expected: `ls /opt/odoo17/custom_addons/lms_bridge/__manifest__.py` exists

```
[ ] 18. Create the Odoo data directory and log directory.
        sudo mkdir -p /opt/odoo/data
        sudo mkdir -p /var/log/odoo17
        sudo chown odoo:odoo /opt/odoo/data /var/log/odoo17
        sudo chmod 750 /opt/odoo/data
```
✓ Expected: Both directories exist and are owned by the `odoo` user

```
[ ] 19. Restore the filestore.
        sudo mkdir -p /opt/odoo/data/filestore/odoo_lms_production
        sudo rsync -a /tmp/odoo_import_*/filestore/odoo_lms_test/ \
          /opt/odoo/data/filestore/odoo_lms_production/
        sudo chown -R odoo:odoo /opt/odoo/data/filestore/
```
✓ Expected: `du -sh /opt/odoo/data/filestore/odoo_lms_production/` shows ~13 MB or more

---

## Section 4 — odoo17.conf for Production `~5 min`

**Goal:** Config file tuned for a real multi-core server with proper paths.

```
[ ] 20. Create /etc/odoo17.conf with production values.
        sudo tee /etc/odoo17.conf << 'EOF'
        [options]
        ; ─────────────────────────────────────────────
        ; Odoo 17 Community — PRODUCTION Config
        ; IntZam Microfinance / CirclePay Zambia
        ; ─────────────────────────────────────────────

        ; --- Server ---
        http_port = 8069
        xmlrpc_port = 8069
        ; Bind only to localhost — Nginx handles external traffic
        xmlrpc_interface = 127.0.0.1
        netrpc_interface = 127.0.0.1

        ; --- Database ---
        db_host = localhost
        db_port = 5432
        db_user = odoo_user
        db_password = CHANGE_ME_strong_db_password
        db_name = odoo_lms_production
        db_maxconn = 64
        db_sslmode = prefer

        ; --- Addons ---
        addons_path = /opt/odoo17/addons,/opt/odoo17/custom_addons

        ; --- Logging ---
        logfile = /var/log/odoo17/odoo.log
        log_level = warn
        log_db = False

        ; --- Security ---
        ; Generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
        admin_passwd = CHANGE_ME_new_master_password_not_admin_master_2025

        ; --- Workers (set to nCPU - 1, min 2) ---
        ; 4-core server: workers = 3
        ; 2-core server: workers = 2
        workers = 3
        max_cron_threads = 1

        ; --- Data ---
        data_dir = /opt/odoo/data

        ; --- Performance (production) ---
        limit_memory_hard = 2684354560
        limit_memory_soft = 2147483648
        limit_request = 8192
        limit_time_cpu = 60
        limit_time_real = 120
        limit_time_real_cron = 300
        EOF

        sudo chmod 640 /etc/odoo17.conf
        sudo chown root:odoo /etc/odoo17.conf
```
✓ Expected: `sudo cat /etc/odoo17.conf` shows the file; `odoo` group can read it

⚠ Watch out: Change EVERY `CHANGE_ME` value before starting Odoo.
  The test admin_passwd `admin_master_2025` MUST be replaced.

```
[ ] 21. Verify Odoo can read the config and connect to the database.
        sudo -u odoo /opt/odoo17/venv/bin/python /opt/odoo17/odoo-bin \
          --config=/etc/odoo17.conf \
          --stop-after-init \
          --database=odoo_lms_production \
          --no-http 2>&1 | tail -10
```
✓ Expected: Last lines show no CRITICAL or ERROR entries. A single run that ends
  cleanly (exit 0) confirms DB connectivity.

---

## Section 5 — Systemd Service `~5 min`

**Goal:** Odoo starts automatically on boot, restarts on crash.

```
[ ] 22. Create the systemd unit file.
        sudo tee /etc/systemd/system/odoo17.service << 'EOF'
        [Unit]
        Description=Odoo 17 Community — IntZam LMS
        Documentation=https://www.odoo.com
        After=network.target postgresql.service
        Requires=postgresql.service

        [Service]
        Type=simple
        User=odoo
        Group=odoo
        ExecStart=/opt/odoo17/venv/bin/python /opt/odoo17/odoo-bin \
          --config=/etc/odoo17.conf \
          --logfile=/var/log/odoo17/odoo.log
        Restart=on-failure
        RestartSec=5s
        KillMode=mixed
        StandardOutput=journal
        StandardError=journal
        SyslogIdentifier=odoo17

        ; Security hardening
        NoNewPrivileges=true
        PrivateTmp=true
        ProtectSystem=full

        [Install]
        WantedBy=multi-user.target
        EOF
```
✓ Expected: File created at `/etc/systemd/system/odoo17.service`

```
[ ] 23. Enable and start the service.
        sudo systemctl daemon-reload
        sudo systemctl enable odoo17
        sudo systemctl start odoo17
```
✓ Expected: `sudo systemctl status odoo17` shows `active (running)`

```
[ ] 24. Confirm Odoo is responding on localhost:8069.
        curl -s http://127.0.0.1:8069/web/health
```
✓ Expected: `{"status": "pass"}`

```
[ ] 25. Check the log for startup errors.
        sudo tail -30 /var/log/odoo17/odoo.log
```
✓ Expected: No CRITICAL lines; last lines contain `HTTP service running on`

---

## Section 6 — Nginx Reverse Proxy + SSL `~15 min`

**Goal:** HTTPS on port 443, HTTP redirects to HTTPS, Odoo proxied from 8069.

```
[ ] 26. Create the Nginx server block.
        sudo tee /etc/nginx/sites-available/odoo17 << 'EOF'
        # HTTP → HTTPS redirect
        server {
            listen 80;
            server_name odoo.YOUR_DOMAIN.com;
            return 301 https://$host$request_uri;
        }

        # HTTPS — Odoo proxy
        server {
            listen 443 ssl http2;
            server_name odoo.YOUR_DOMAIN.com;

            # SSL certs — filled by certbot
            ssl_certificate     /etc/letsencrypt/live/odoo.YOUR_DOMAIN.com/fullchain.pem;
            ssl_certificate_key /etc/letsencrypt/live/odoo.YOUR_DOMAIN.com/privkey.pem;
            ssl_protocols       TLSv1.2 TLSv1.3;
            ssl_ciphers         HIGH:!aNULL:!MD5;
            ssl_session_cache   shared:SSL:10m;
            ssl_session_timeout 10m;

            # Security headers
            add_header X-Frame-Options        SAMEORIGIN;
            add_header X-Content-Type-Options nosniff;
            add_header X-XSS-Protection       "1; mode=block";
            add_header Strict-Transport-Security "max-age=31536000" always;

            # Proxy settings
            proxy_read_timeout    720s;
            proxy_connect_timeout 720s;
            proxy_send_timeout    720s;

            # Longpolling (Odoo real-time / bus)
            location /longpolling {
                proxy_pass http://127.0.0.1:8072;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
            }

            # All other requests
            location / {
                proxy_pass http://127.0.0.1:8069;
                proxy_set_header Host              $host;
                proxy_set_header X-Real-IP         $remote_addr;
                proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_redirect off;
            }

            # Static files — serve directly from Odoo's whitenoise storage
            location ~* /web/static/ {
                proxy_cache_valid 200 90d;
                proxy_buffering   on;
                proxy_pass        http://127.0.0.1:8069;
                proxy_set_header  Host $host;
                expires           max;
                add_header        Cache-Control public;
            }

            # File upload size (match Odoo's limit)
            client_max_body_size 200m;

            access_log /var/log/nginx/odoo17.access.log;
            error_log  /var/log/nginx/odoo17.error.log warn;
        }
        EOF

        sudo ln -sf /etc/nginx/sites-available/odoo17 /etc/nginx/sites-enabled/
        sudo nginx -t
```
✓ Expected: `nginx: configuration file ... test is successful`

⚠ Watch out: Replace `odoo.YOUR_DOMAIN.com` with your actual domain before this step.
  SSL cert paths will not exist yet — that's fine; certbot fills them in step 27.

```
[ ] 27. Obtain a Let's Encrypt SSL certificate.
        # Temporarily allow plain HTTP so certbot can do its challenge:
        sudo nginx -t && sudo systemctl reload nginx
        sudo certbot --nginx \
          -d odoo.YOUR_DOMAIN.com \
          --non-interactive \
          --agree-tos \
          --email admin@YOUR_DOMAIN.com \
          --redirect
```
✓ Expected: `Congratulations! Your certificate and chain have been saved`

```
[ ] 28. Reload Nginx with the full HTTPS config.
        sudo systemctl reload nginx
```
✓ Expected: `curl -I https://odoo.YOUR_DOMAIN.com/web/health` returns `HTTP/2 200`

```
[ ] 29. Enable certbot auto-renewal (certbot installs a timer by default).
        sudo systemctl status certbot.timer
```
✓ Expected: Timer is `active (waiting)`; dry-run: `sudo certbot renew --dry-run`

```
[ ] 30. Add the proxy header to odoo17.conf so Odoo sees real client IPs.
        # Add this line under [options]:
        proxy_mode = True
        # Then restart:
        sudo systemctl restart odoo17
```
✓ Expected: Odoo logs now show client IPs instead of 127.0.0.1

---

## Section 7 — .env.production Credentials `~5 min`

**Goal:** LMS Django backend points to production Odoo, not localhost:8069.

```
[ ] 31. On the production LMS server (or CI/CD), populate .env.production.
        The following values MUST change from the test/WSL values:
```

| Variable | WSL (test) value | Production value |
|---|---|---|
| `APP_ENV` | `local` | `production` |
| `SECRET_KEY` | insecure dev key | `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `True` | `False` |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | `postgresql://lms_user:PW@localhost:5432/lms_production` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `api.YOUR_DOMAIN.com` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | `https://app.YOUR_DOMAIN.com` |
| `ODOO_URL` | `http://localhost:8069` | `http://127.0.0.1:8069` ¹ |
| `ODOO_DB` | `odoo_lms_test` | `odoo_lms_production` |
| `ODOO_USER` | `admin` | dedicated service account (see step 32) |
| `ODOO_PASSWORD` | `admin1234` | strong password for service account |

> ¹ If LMS and Odoo run on the same server, use `http://127.0.0.1:8069` (internal).
>   If on separate servers, use the private/VPN IP — never expose 8069 publicly.

```
[ ] 32. Create a dedicated Odoo service account (do not use admin).
        In Odoo UI: Settings → Users → New User
          - Name: LMS Service Account
          - Login: lms_service
          - Role: Billing (gives full Accounting access)
          - Technical Features: enable if needed for XML-RPC model access
          - Set a strong password
        Update ODOO_USER and ODOO_PASSWORD in .env.production.
```
✓ Expected: Service account can authenticate via XML-RPC (tested in section 8)

```
[ ] 33. Restrict file permissions on .env.production.
        chmod 600 /opt/lms/backend/.env.production
        chown lms_app:lms_app /opt/lms/backend/.env.production
```
✓ Expected: `ls -la .env.production` shows `-rw-------`

```
[ ] 34. Apply Django migrations on the production LMS database.
        cd /opt/lms/backend
        APP_ENV=production python manage.py migrate --run-syncdb
        APP_ENV=production python manage.py collectstatic --noinput
```
✓ Expected: All migrations applied with no errors; `staticfiles/` populated

---

## Section 8 — Smoke-Test XML-RPC Connection `~5 min`

**Goal:** Confirm LMS can authenticate to Odoo and post a test journal entry.

```
[ ] 35. Run the connection test script from the LMS backend.
        cd /opt/lms/backend
        APP_ENV=production python3 test_odoo_connection.py
```
✓ Expected (all 7 tests pass):
```
  ✓ Odoo health endpoint: {"status": "pass"}
  ✓ server_version : 17.0
  ✓ Authenticated as UID <N>
  ✓ Found N partner(s)
  ✓ lms.loan.event accessible — 0 records in audit log
  ✓ LDIS  id=N  type=general  name=Loan Disbursement Journal
  ✓ LRPY  id=N  type=bank     name=Loan Repayment Journal
  ✓ LINT  id=N  ...
  ✓ LFEE  id=N  ...
  ✓ LPROV id=N  ...
  ✓ ping() returned: {'server_version': '17.0', 'auth_status': 'ok', ...}
```

⚠ Watch out: If test 3 (authentication) fails with the service account, verify
  the account is active and has `Accounting / Billing` access rights in Odoo.

```
[ ] 36. Post a synthetic disbursement via the Django shell to verify end-to-end.
        cd /opt/lms/backend
        APP_ENV=production python manage.py shell << 'PYEOF'
        from apps.accounting.odoo_client import get_odoo_client
        from datetime import date

        c = get_odoo_client()

        # Create a fake loan-like object for testing
        class FakeLoan:
            loan_number    = 'SMOKE-TEST-001'
            amount         = 100.00
            disbursement_date = date.today()
            term_months    = 1
            interest_rate  = 5.0
            class client:
                name = 'Smoke Test Client'

        class FakeClient:
            id               = 99999
            name             = 'Smoke Test Client'
            phone            = '+260977000099'
            email            = 'smoketest@intzam.local'
            nrc_number       = 'SMOKE-99999'
            address          = 'Test Address'
            tier             = 'BRONZE'
            employment_status = 'EMPLOYED'

        loan          = FakeLoan()
        loan.client   = FakeClient()

        # Step 1: Sync partner
        partner_id = c.sync_borrower(loan.client)
        print(f'Partner synced: id={partner_id}')

        # Step 2: Post disbursement
        move_id = c.post_disbursement(loan, partner_id=partner_id)
        print(f'Disbursement posted: move_id={move_id}')
        print('SMOKE TEST PASSED')
        PYEOF
```
✓ Expected:
```
  Partner synced: id=<N>
  Disbursement posted: move_id=<N>
  SMOKE TEST PASSED
```

```
[ ] 37. Verify the smoke-test journal entry appeared in Odoo.
        In Odoo UI: Accounting → Journal Entries
        Filter by Reference: DISB-SMOKE-TEST-001-*
```
✓ Expected: One posted entry, journal=LDIS, Dr 1111 / Cr 1105, amount=100.00

```
[ ] 38. Delete the smoke-test data from Odoo (keep prod clean).
        In Odoo UI:
          - Reset the journal entry to draft, then delete it.
          - Delete the res.partner 'Smoke Test Client' (ref=LMS-99999).
        Or via psql:
          psql -U odoo_user -d odoo_lms_production -c "
            DELETE FROM account_move WHERE ref LIKE 'DISB-SMOKE-TEST%';
            DELETE FROM res_partner WHERE ref = 'LMS-99999';
          "
```
✓ Expected: No SMOKE-TEST records remain in either table

---

## Section 9 — Verify Journal Entries Post-Deployment `~10 min`

**Goal:** Run at least one real loan lifecycle through the system to confirm
double-entry is correct before going live.

```
[ ] 39. In the LMS UI: create a test client and submit a small loan (ZMW 500).
        - Client NRC: 123456/10/1 (or any valid NRC)
        - Amount: 500.00 ZMW, Term: 1 month, Product: any active product
```
✓ Expected: Loan record in PENDING_APPROVAL status

```
[ ] 40. Approve the loan (as ADMIN or UNDERWRITER role).
        POST /api/loans/<id>/approve/
```
✓ Expected: Loan status → APPROVED

```
[ ] 41. Disburse the loan (as ADMIN or ACCOUNTANT role).
        POST /api/loans/<id>/disburse/
```
✓ Expected:
- Loan status → ACTIVE
- LMS log: `Disbursement posted to Odoo: loan=LN... move_id=<N>`
- `loan.odoo_partner_id` and `loan.odoo_disbursement_move_id` are populated

```
[ ] 42. Check the journal entry in Odoo.
        Accounting → Journal Entries → filter by Journal: LDIS
```
✓ Expected:

| | Account | Debit | Credit |
|--|--|--|--|
| Dr | 1111 Loan Receivable S1 | 500.00 | — |
| Cr | 1105 Bank Clearing (ZMW) | — | 500.00 |

Status: **Posted** ✓

```
[ ] 43. Post a repayment for the full amount.
        POST /api/loans/<id>/repay/
        Body: {"amount": <total_repayable>}
```
✓ Expected:
- Transaction recorded in LMS
- LMS log: `Repayment posted to Odoo: loan=LN... move_id=<N>`

```
[ ] 44. Check the repayment journal entry in Odoo.
        Accounting → Journal Entries → filter by Journal: LRPY
```
✓ Expected:

| | Account | Debit | Credit |
|--|--|--|--|
| Dr | 1105 Bank Clearing (ZMW) | total | — |
| Cr | 1111 Loan Receivable S1 | principal | — |
| Cr | 4101 Interest Income S1 | interest | — |

Status: **Posted** ✓

```
[ ] 45. Check the lms.loan.event audit log in Odoo.
        LMS Bridge → Loan Events
```
✓ Expected: Two rows for the test loan — one `disbursement` (posted), one `repayment` (posted)

```
[ ] 46. Trial balance sanity check.
        Accounting → Reporting → Trial Balance (filter: today)
        Verify that Total Debit = Total Credit (balanced).
```
✓ Expected: The trial balance is perfectly balanced; no orphaned entries

---

## Section 10 — Go-Live Final Checks `~10 min`

```
[ ] 47. Remove or disable the Odoo database manager for security.
        In odoo17.conf add:
          list_db = False
        Then restart: sudo systemctl restart odoo17
```
✓ Expected: Navigating to `/web/database/manager` returns a 404 or blank

```
[ ] 48. Confirm cron jobs are running.
        In Odoo UI: Settings → Technical → Automation → Scheduled Actions
        Check that "Base: Auto-vacuum internal data" last run ≤ 24h ago.
```
✓ Expected: All scheduled actions have a recent Last Execution date

```
[ ] 49. Set up log rotation for Odoo logs.
        sudo tee /etc/logrotate.d/odoo17 << 'EOF'
        /var/log/odoo17/*.log {
            daily
            missingok
            rotate 30
            compress
            delaycompress
            notifempty
            sharedscripts
            postrotate
                systemctl reload odoo17 2>/dev/null || true
            endscript
        }
        EOF
```
✓ Expected: `sudo logrotate --debug /etc/logrotate.d/odoo17` shows no errors

```
[ ] 50. Schedule a nightly database backup.
        sudo tee /etc/cron.d/odoo-backup << 'EOF'
        # Nightly Odoo DB backup at 02:00
        0 2 * * * odoo pg_dump -h localhost -U odoo_user odoo_lms_production \
          | gzip > /opt/odoo/backups/odoo_lms_production_$(date +\%Y\%m\%d).sql.gz
        EOF

        sudo mkdir -p /opt/odoo/backups
        sudo chown odoo:odoo /opt/odoo/backups
```
✓ Expected: After midnight, `ls /opt/odoo/backups/*.gz` shows today's backup

```
[ ] 51. Monitor Odoo memory usage for the first 48 hours.
        watch -n5 'ps aux | grep odoo | grep -v grep | \
          awk "{sum+=\$6} END {print sum/1024\" MB\"}"'
```
✓ Expected: Stable memory, no worker processes exceeding 2 GB individually

```
[ ] 52. Set up uptime monitoring (optional but recommended).
        Use UptimeRobot (free), Freshping, or your own Prometheus stack.
        Monitor: https://odoo.YOUR_DOMAIN.com/web/health
        Alert if response > 5s or status ≠ 200.
```
✓ Expected: Monitoring dashboard shows green

---

## Quick Reference: Key Files Changed from WSL → Production

| File | WSL value | Production change |
|---|---|---|
| `/etc/odoo17.conf` | `workers = 0` | `workers = 3` (or nCPU−1) |
| `/etc/odoo17.conf` | `data_dir = /home/mufwaya/...` | `data_dir = /opt/odoo/data` |
| `/etc/odoo17.conf` | `admin_passwd = admin_master_2025` | New 32-char random token |
| `/etc/odoo17.conf` | `db_name = odoo_lms_test` | `db_name = odoo_lms_production` |
| `/etc/odoo17.conf` | `log_level = info` | `log_level = warn` |
| `/etc/odoo17.conf` | `limit_time_cpu = 600` | `limit_time_cpu = 60` |
| `backend/.env` | `APP_ENV=local` | `APP_ENV=production` |
| `backend/.env` | `ODOO_USER=admin` | `ODOO_USER=lms_service` |
| `backend/.env` | `ODOO_DB=odoo_lms_test` | `ODOO_DB=odoo_lms_production` |
| `backend/.env` | `DATABASE_URL=sqlite:///` | PostgreSQL URL |
| `backend/.env` | `DEBUG=True` | `DEBUG=False` |

---

*Generated: 2026-03-14 | IntZam Microfinance LMS v1.0 | Odoo 17.0.1.0.0*
