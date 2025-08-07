# 📡 NOC Data Visualization & Storage Dashboard (Django)

This is a Django-based Network Operations Center (NOC) dashboard designed to help visualize, store, and manage network event data. It was originally built for internal use in a real-world company environment and is now open-sourced to showcase its architecture and functionality.

---

## 🚀 Features

- 📊 Visualize network uptime, downtime, and related events
- 📁 Import and manage events via CSV
- 🗓️ Integration with Google Calendar API (event syncing)
- 🔒 Admin panel to manage hosts, events, and users
- 📈 Real-time updates and historical tracking

---

## 🧰 Tech Stack

- **Framework:** Django
- **Frontend:** HTML, Bootstrap (Django templates)
- **Database:** SQLite3 (for development)
- **API Integration:** Google Calendar API

---

## 📂 Project Structure

```
host_report/
├── base/                   # Django app with core logic
├── host_report/            # Project settings and URLs
├── new_events_to_create.csv # Sample event data
├── credentials.json        # Google API credentials
├── db.sqlite3              # Development DB
└── manage.py               # Entry point
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/noc-dashboard.git
cd noc-dashboard
```

### 2. Set up virtual environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> Or manually install:
```bash
pip install django google-auth-oauthlib google-api-python-client
```

### 4. Migrate the database

```bash
python manage.py migrate
```

### 5. Run the development server

```bash
python manage.py runserver
```

Open in browser: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🔐 Google Calendar Integration

To enable event syncing with Google Calendar:

1. Get `credentials.json` from [Google Developer Console](https://console.cloud.google.com/).
2. Place it in the root of the project.
3. The first sync will prompt browser authentication.

---

## 👤 Admin Access

To access Django admin panel:

```bash
python manage.py createsuperuser
```

Then log in at: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

## 📌 Notes

> ⚠️ This version contains **mock or example data** only. All sensitive or company-specific configurations have been removed to protect privacy.

---

## 💼 Why This Project?

This app was developed for a real-world use case in a company’s NOC team to monitor and manage network-related events.  
It demonstrates backend integration, event tracking, and external API usage — making it a great portfolio project for showcasing Django development skills.

---

## 📃 License

This codebase is open for educational and portfolio use. Commercial usage is restricted unless permitted.
