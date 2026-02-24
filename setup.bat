@echo off
chcp 65001 >nul
title Telegram Sender — Установка

echo.
echo  ╔══════════════════════════════════════╗
echo  ║     Telegram Sender — Установка      ║
echo  ╚══════════════════════════════════════╝
echo.

:: Проверяем Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python не установлен!
    echo.
    echo  Сейчас откроется страница скачивания.
    echo  Скачай и установи Python, при установке
    echo  обязательно поставь галочку:
    echo  "Add Python to PATH"
    echo.
    echo  После установки Python запусти setup.bat снова.
    echo.
    pause
    start https://python.org/downloads
    exit
)

echo  [OK] Python найден
echo.
echo  Устанавливаю библиотеки...
echo.

pip install telethon flask --quiet --disable-pip-version-check

if %errorlevel% neq 0 (
    echo.
    echo  [!] Ошибка установки. Попробуй запустить от имени администратора.
    pause
    exit
)

echo.
echo  ╔══════════════════════════════════════╗
echo  ║         Установка завершена!         ║
echo  ║                                      ║
echo  ║   Теперь запусти файл start.bat      ║
echo  ╚══════════════════════════════════════╝
echo.
pause
