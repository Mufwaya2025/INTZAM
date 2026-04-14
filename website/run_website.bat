@echo off
setlocal

cd /d %~dp0

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing requirements...
python -m pip install -r requirements.txt

echo Applying migrations...
python manage.py migrate

echo Seeding default website content...
python manage.py seed_website

echo Starting standalone website server...
python manage.py runserver

endlocal
