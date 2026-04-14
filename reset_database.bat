@echo off
echo ========================================
echo Resetting Database - IntZam LMS
echo ========================================
echo.

echo Step 1: Stopping backend server...
echo Please manually stop the backend server (Ctrl+C in the terminal running it)
echo Press any key after stopping the server...
pause > nul

echo.
echo Step 2: Deleting old database...
cd backend
if exist db.sqlite3 (
    del /F db.sqlite3
    echo Database deleted successfully
) else (
    echo Database file not found
)

echo.
echo Step 3: Running migrations...
venv\Scripts\python.exe manage.py migrate

echo.
echo Step 4: Seeding database with clean data...
venv\Scripts\python.exe manage.py seed_data

echo.
echo ========================================
echo Database reset complete!
echo ========================================
echo.
echo You can now start the backend server with:
echo    cd backend
echo    venv\Scripts\python.exe manage.py runserver
echo.
echo Login with:
echo    Username: admin
echo    Password: admin123
echo.
pause
