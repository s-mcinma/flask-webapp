# Email & Address Manager — Flask on Apache / EC2

A Flask web application that stores email addresses and physical addresses in an
AWS RDS MySQL database (provisioned with the AWS *dev/test* template).

---

## Bugs fixed from the original repo

| File | Issue | Fix |
|---|---|---|
| `requirements.txt` | `pyhton-dotenv` typo | → `python-dotenv` |
| `templates/bases.html` | Wrong filename — templates extend `base.html` | Renamed to `base.html` |
| `app.py` | `load_dotenv()` never called despite being a dependency | Added import + call |
| `app.py` | DB config silently used placeholder strings when env vars missing | Now logs clearly and returns `None` |
| `app.py` | Dev server bound to port 80 (requires root) | Changed default to 5000 for dev |
| *(missing)* | No Apache config or WSGI entry point | Added `webapp.conf` + `webapp.wsgi` |

---

## Project structure

```
webapp/
├── app.py              # Flask application
├── webapp.wsgi         # mod_wsgi entry point (production)
├── webapp.conf         # Apache VirtualHost config
├── requirements.txt
├── .env.example        # Copy to .env and fill in your values
└── templates/
    ├── base.html       # Base layout (was incorrectly named bases.html)
    ├── index.html      # Home page — add / check emails & addresses
    └── view_data.html  # Data table view
```

---

## EC2 + Apache setup (Amazon Linux 2023)

### 1 — Install system packages

```bash
sudo dnf update -y
sudo dnf install -y httpd python3 python3-pip mod_wsgi
sudo systemctl enable --now httpd
```

### 2 — Deploy the application

```bash
sudo mkdir -p /var/www/webapp
sudo cp -r * /var/www/webapp/
sudo chown -R apache:apache /var/www/webapp
```

### 3 — Install Python dependencies

```bash
sudo pip3 install -r /var/www/webapp/requirements.txt
```

### 4 — Configure environment variables

**Option A — .env file (recommended for simplicity)**

```bash
sudo cp /var/www/webapp/.env.example /var/www/webapp/.env
sudo nano /var/www/webapp/.env   # fill in real values
sudo chmod 640 /var/www/webapp/.env
sudo chown apache:apache /var/www/webapp/.env
```

**Option B — Apache SetEnv directives**

Uncomment the `SetEnv` lines in `webapp.conf` and fill in your values.

### 5 — Install the Apache config

```bash
sudo cp /var/www/webapp/webapp.conf /etc/httpd/conf.d/webapp.conf
sudo systemctl restart httpd
```

### 6 — Open port 80 in your Security Group

In the AWS Console → EC2 → Security Groups, add an inbound rule:
- Type: HTTP, Port: 80, Source: 0.0.0.0/0 (or restrict as needed)

---

## RDS setup (dev/test template)

1. Create an RDS MySQL instance using the **Dev/Test** template.
2. Set the DB name to `webapp_db` (or update `DB_NAME` in your `.env`).
3. Ensure the RDS Security Group allows inbound MySQL (port 3306) from your
   EC2 instance's Security Group.
4. The app creates the `emails` and `addresses` tables automatically on first
   start — no manual schema setup required.

---

## Development (local / without Apache)

```bash
cp .env.example .env        # fill in your RDS details
pip install -r requirements.txt
python3 app.py               # runs on http://localhost:5000
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page (add / check data) |
| GET | `/view_data` | HTML table of all stored data |
| GET | `/api/emails` | JSON — all emails with address counts |
| GET | `/health` | Health check — returns DB connectivity status |

---

## Security notes

- Never commit `.env` to version control — it's in `.gitignore` by default.
- Rotate `SECRET_KEY` before going to production.
- Restrict the RDS Security Group to your EC2 instance only.
- Consider enabling HTTPS via AWS Certificate Manager + an ALB.
