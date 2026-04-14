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

echo Creating admin user...
python manage.py createsuperuser

endlocal
