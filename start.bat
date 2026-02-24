@echo off
chcp 65001 >nul
title Telegram Sender

:: Проверяем Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python не найден. Сначала запусти setup.bat
    pause
    exit
)

echo  Запускаю Telegram Sender...
echo  Сейчас откроется браузер.
echo.
echo  Чтобы остановить — закрой это окно.
echo.

:: Открываем браузер через 2 секунды
start "" timeout /t 2 >nul & start http://localhost:5000

:: Запускаем сервер
python web_interface.py

pause
