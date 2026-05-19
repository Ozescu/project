# Application de Gestion de Bibliothèque Intelligente

Demo Django app for library management with roles, catalogue, loans, reservations, sanctions, notifications and recommendations.

Quick start:

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Start the development server:

```bash
python manage.py migrate
python manage.py runserver
```

`runserver` applies missing migrations and seeds demo data automatically on a fresh checkout.

Demo accounts:
- admin / admin12345
- biblio / biblio12345
- lecteur / lecteur12345

Notes:
- Uses SQLite by default. See `config/settings.py` for a PostgreSQL example.
- Emails are printed to console by default.
