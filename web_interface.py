"""
Telegram Sender — Веб-интерфейс
"""

import os
import json
import csv
import subprocess
import sys
from datetime import date
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

CONTACTS_FILE = "contacts.csv"
PROGRESS_FILE = "progress.json"
CONFIG_FILE = "config.json"

SETUP_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Настройка — Telegram Sender</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg:#eef2f7;--white:#fff;--blue:#4a7fff;--blue-light:#e8efff;--text:#2d3a52;--muted:#8a97b0;--border:#dde4f0;--red:#f06060;--red-bg:#fff0f0; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }
  .box { background:var(--white); border-radius:20px; padding:40px; max-width:520px; width:100%; box-shadow:0 8px 40px rgba(74,127,255,0.1); border:1px solid var(--border); }
  .logo { display:flex; align-items:center; gap:12px; margin-bottom:28px; }
  .logo-icon { width:44px; height:44px; background:var(--blue-light); border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:20px; }
  h1 { font-size:20px; font-weight:700; }
  .sub { font-size:12px; color:var(--muted); margin-top:2px; }
  .step { display:flex; gap:12px; margin-bottom:20px; padding:14px; background:var(--bg); border-radius:12px; border:1px solid var(--border); }
  .num { width:26px; height:26px; background:var(--blue); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:#fff; flex-shrink:0; }
  .step-text { font-size:13px; color:var(--muted); line-height:1.6; }
  .step-text a { color:var(--blue); font-weight:500; }
  .fg { margin-bottom:14px; }
  label { display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:5px; }
  input, textarea { width:100%; background:var(--bg); border:1.5px solid var(--border); border-radius:10px; color:var(--text); padding:11px 13px; font-size:13px; font-family:'Inter',sans-serif; outline:none; }
  input:focus, textarea:focus { border-color:var(--blue); background:#fff; }
  textarea { resize:vertical; min-height:90px; }
  .hint { font-size:11px; color:var(--muted); margin-top:4px; }
  .btn { width:100%; padding:13px; background:var(--blue); color:#fff; border:none; border-radius:10px; font-size:14px; font-weight:600; cursor:pointer; margin-top:6px; font-family:'Inter',sans-serif; }
  .btn:hover { background:#3a6fef; }
  .err { background:var(--red-bg); border:1px solid rgba(240,96,96,0.3); color:var(--red); border-radius:10px; padding:11px 14px; margin-bottom:14px; font-size:13px; }
</style>
</head>
<body>
<div class="box">
  <div class="logo">
    <div class="logo-icon">📨</div>
    <div><h1>Первый запуск</h1><div class="sub">настройка займёт 2 минуты</div></div>
  </div>
  <div class="step">
    <div class="num">1</div>
    <div class="step-text">Зайди на <a href="https://my.telegram.org" target="_blank">my.telegram.org</a> → войди своим номером → <strong>"API Development Tools"</strong> → заполни название (любое) → получишь <strong>api_id</strong> и <strong>api_hash</strong></div>
  </div>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST" action="/setup">
    <div class="fg"><label>API ID (число)</label><input type="text" name="api_id" placeholder="12345678" required value="{{ form.api_id or '' }}"></div>
    <div class="fg"><label>API Hash</label><input type="text" name="api_hash" placeholder="0123456789abcdef..." required value="{{ form.api_hash or '' }}"></div>
    <div class="fg">
      <label>Текст рассылки</label>
      <textarea name="message" placeholder="Привет! Напиши своё сообщение.&#10;Можно использовать {name} — подставится имя.">{{ form.message or '' }}</textarea>
      <div class="hint">Используй {name} для подстановки имени контакта</div>
    </div>
    <div class="fg"><label>Файл для прикрепления (необязательно)</label><input type="text" name="attachment" placeholder="document.pdf или оставь пустым" value="{{ form.attachment or '' }}"></div>
    <button type="submit" class="btn">Сохранить и продолжить →</button>
  </form>
</div>
</body>
</html>
"""

MAIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Telegram Sender</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#eef2f7; --white:#fff; --blue:#4a7fff; --blue-light:#e8efff; --blue-mid:#c5d8ff;
    --text:#2d3a52; --muted:#8a97b0; --border:#dde4f0;
    --green:#34c48b; --green-bg:#eafaf3; --orange:#f5a623; --orange-bg:#fff8ec; --red:#f06060; --red-bg:#fff0f0;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; display:flex; }

  .sidebar { width:220px; flex-shrink:0; background:var(--white); min-height:100vh; padding:24px 0;
             display:flex; flex-direction:column; box-shadow:4px 0 20px rgba(74,127,255,0.06);
             position:fixed; top:0; left:0; bottom:0; }
  .sidebar-logo { display:flex; align-items:center; gap:10px; padding:0 18px 22px; border-bottom:1px solid var(--border); margin-bottom:14px; }
  .logo-icon { width:36px; height:36px; background:var(--blue-light); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; }
  .logo-name { font-size:14px; font-weight:700; }
  .logo-sub { font-size:10px; color:var(--muted); }
  .nav-section { padding:0 10px; margin-bottom:8px; }
  .nav-label { font-size:10px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.8px; padding:0 8px; margin-bottom:4px; }
  .nav-item { display:flex; align-items:center; gap:9px; padding:9px 10px; border-radius:10px; cursor:pointer;
              font-size:13px; font-weight:500; color:var(--muted); transition:all .15s; text-decoration:none; margin-bottom:2px; background:none; border:none; width:100%; font-family:'Inter',sans-serif; }
  .nav-item:hover { background:var(--blue-light); color:var(--blue); }
  .nav-item.active { background:var(--blue); color:#fff; }
  .nav-icon { font-size:14px; width:18px; text-align:center; }
  .nav-badge { margin-left:auto; background:var(--blue); color:#fff; border-radius:999px; font-size:10px; font-weight:700; padding:1px 7px; }
  .nav-item.active .nav-badge { background:rgba(255,255,255,.25); }
  .sidebar-bottom { margin-top:auto; padding:16px 18px 0; border-top:1px solid var(--border); }
  .user-row { display:flex; align-items:center; gap:10px; }
  .user-avatar { width:34px; height:34px; border-radius:50%; background:var(--blue-light); display:flex; align-items:center; justify-content:center; font-size:15px; }
  .user-name { font-size:13px; font-weight:600; }
  .user-status { font-size:11px; color:var(--green); font-weight:500; }

  .main { margin-left:220px; flex:1; padding:30px 26px; min-height:100vh; }
  .page-header { margin-bottom:22px; }
  .page-header h1 { font-size:20px; font-weight:700; }
  .page-header p { font-size:12px; color:var(--muted); margin-top:3px; }

  .flash { padding:12px 16px; border-radius:10px; margin-bottom:18px; font-size:13px; font-weight:500; }
  .flash-ok { background:var(--green-bg); color:var(--green); border:1px solid #b8f0d8; }
  .flash-err { background:var(--red-bg); color:var(--red); border:1px solid #ffc5c5; }

  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:13px; margin-bottom:18px; }
  .card { background:var(--white); border-radius:14px; padding:18px; box-shadow:0 2px 12px rgba(74,127,255,.07); border:1px solid var(--border); }
  .card-icon { width:42px; height:42px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:19px; margin-bottom:12px; }
  .ci-blue { background:var(--blue-light); } .ci-green { background:var(--green-bg); } .ci-orange { background:var(--orange-bg); } .ci-red { background:var(--red-bg); }
  .card-label { font-size:11px; color:var(--muted); font-weight:500; margin-bottom:3px; }
  .card-num { font-size:28px; font-weight:700; letter-spacing:-1px; }
  .card-sub { font-size:11px; color:var(--blue); font-weight:500; margin-top:3px; }

  .section { background:var(--white); border-radius:14px; padding:20px; box-shadow:0 2px 12px rgba(74,127,255,.07); border:1px solid var(--border); }
  .section-title { font-size:13px; font-weight:700; margin-bottom:14px; display:flex; align-items:center; gap:7px; }
  .tdot { width:7px; height:7px; border-radius:50%; background:var(--blue); flex-shrink:0; }

  textarea, input[type=text] { width:100%; background:var(--bg); border:1.5px solid var(--border); border-radius:10px; color:var(--text); padding:11px 13px; font-size:13px; font-family:'Inter',sans-serif; transition:border-color .2s; outline:none; }
  textarea { resize:vertical; min-height:108px; }
  textarea:focus, input:focus { border-color:var(--blue); background:#fff; }
  .hint { font-size:11px; color:var(--muted); margin-top:5px; }

  .btn { display:inline-flex; align-items:center; gap:6px; padding:9px 16px; border-radius:9px; border:none;
         cursor:pointer; font-size:13px; font-weight:600; font-family:'Inter',sans-serif; transition:all .15s; }
  .btn-blue { background:var(--blue); color:#fff; }
  .btn-blue:hover { background:#3a6fef; transform:translateY(-1px); }
  .btn-launch { background:linear-gradient(135deg,var(--green),#28b07a); color:#fff; font-size:14px; padding:13px 24px; width:100%; justify-content:center; border-radius:11px; }
  .btn-launch:hover { transform:translateY(-1px); box-shadow:0 6px 16px rgba(52,196,139,.3); }
  .btn-launch:disabled { opacity:.4; cursor:not-allowed; transform:none; box-shadow:none; }
  .btn-ghost { background:var(--blue-light); color:var(--blue); }
  .btn-ghost:hover { background:var(--blue-mid); }
  .btn-danger { background:var(--red-bg); color:var(--red); }
  .btn-danger:hover { background:#ffe0e0; }

  .upload-zone { border:2px dashed var(--border); border-radius:11px; padding:22px; text-align:center; cursor:pointer; transition:all .2s; background:var(--bg); position:relative; }
  .upload-zone:hover { border-color:var(--blue); background:var(--blue-light); }
  .upload-zone input[type=file] { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; }
  .upload-icon { font-size:24px; margin-bottom:6px; }
  .upload-title { font-size:13px; font-weight:600; margin-bottom:2px; }
  .upload-sub { font-size:11px; color:var(--muted); }
  .file-tag { display:inline-flex; align-items:center; gap:5px; margin-top:10px; background:var(--green-bg); border:1px solid #b8f0d8; border-radius:7px; padding:4px 10px; font-size:12px; color:var(--green); font-weight:600; }

  .progress-bar { background:var(--blue-light); border-radius:999px; height:7px; overflow:hidden; }
  .progress-fill { height:7px; border-radius:999px; background:linear-gradient(90deg,var(--blue),#7aa8ff); }
  .progress-label { display:flex; justify-content:space-between; font-size:11px; color:var(--muted); margin-top:5px; font-weight:500; }

  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; font-size:10px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; padding:0 12px 9px; border-bottom:1px solid var(--border); }
  td { padding:10px 12px; border-bottom:1px solid var(--bg); }
  tr:last-child td { border-bottom:none; }
  tr:hover td { background:var(--bg); }
  .badge { display:inline-flex; align-items:center; gap:3px; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:600; }
  .b-green { background:var(--green-bg); color:var(--green); }
  .b-red { background:var(--red-bg); color:var(--red); }
  .b-gray { background:var(--bg); color:var(--muted); border:1px solid var(--border); }

  .notice { border-radius:9px; padding:11px 14px; font-size:13px; font-weight:500; margin-bottom:13px; }
  .notice-green { background:var(--green-bg); color:var(--green); }
  .notice-orange { background:var(--orange-bg); color:var(--orange); }

  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .controls { display:flex; gap:9px; flex-wrap:wrap; }
  .mb { margin-bottom:14px; }

  @media(max-width:900px) {
    .sidebar { display:none; } .main { margin-left:0; }
    .cards { grid-template-columns:repeat(2,1fr); } .grid2 { grid-template-columns:1fr; }
  }
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-logo">
    <div class="logo-icon">📨</div>
    <div><div class="logo-name">TG Sender</div><div class="logo-sub">рассылка</div></div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Главная</div>
    <a class="nav-item active" href="/"><span class="nav-icon">📊</span> Dashboard</a>
    <a class="nav-item" href="#"><span class="nav-icon">📋</span> История<span class="nav-badge">{{ s.sent }}</span></a>
  </div>
  <div class="nav-section">
    <div class="nav-label">Настройки</div>
    <form method="POST" action="/edit_message" style="display:contents">
      <button type="submit" class="nav-item"><span class="nav-icon">✏️</span> Сообщение</button>
    </form>
  </div>
  <div class="sidebar-bottom">
    <div class="user-row">
      <div class="user-avatar">👤</div>
      <div><div class="user-name">Мой аккаунт</div><div class="user-status">● подключён</div></div>
    </div>
  </div>
</div>

<div class="main">
  <div class="page-header">
    <h1>Dashboard</h1>
    <p>25 контактов в день · 5 штук каждые 5 минут</p>
  </div>

  {% if flash %}<div class="flash {{ flash.cls }}">{{ flash.msg }}</div>{% endif %}

  <div class="cards">
    <div class="card"><div class="card-icon ci-blue">📬</div><div class="card-label">Всего контактов</div><div class="card-num">{{ s.total }}</div><div class="card-sub">в базе</div></div>
    <div class="card"><div class="card-icon ci-green">✅</div><div class="card-label">Отправлено</div><div class="card-num">{{ s.sent }}</div><div class="card-sub">успешно</div></div>
    <div class="card"><div class="card-icon ci-orange">📅</div><div class="card-label">Сегодня</div><div class="card-num">{{ s.today }} <span style="font-size:15px;color:var(--muted);font-weight:400">/ {{ s.limit }}</span></div><div class="card-sub">дневной лимит</div></div>
    <div class="card"><div class="card-icon ci-red">⏳</div><div class="card-label">В очереди</div><div class="card-num">{{ s.pending }}</div><div class="card-sub">ждут отправки</div></div>
  </div>

  <div class="grid2 mb">
    <div class="section">
      <div class="section-title"><span class="tdot"></span>Добавить контакты</div>
      <form method="POST" action="/add">
        <textarea name="contacts" placeholder="+79001234567&#10;+79007654321, Иван Иванов&#10;@username&#10;@vasya, Вася Пупкин"></textarea>
        <div class="hint">по одному на строке · с именем через запятую</div>
        <div style="margin-top:11px"><button type="submit" class="btn btn-blue">Добавить</button></div>
      </form>
    </div>
    <div class="section">
      <div class="section-title"><span class="tdot" style="background:var(--orange)"></span>Прикрепить файл</div>
      <form method="POST" action="/upload_file" enctype="multipart/form-data" id="uploadForm">
        <div class="upload-zone" id="dropZone">
          <input type="file" name="file" id="fileInput" onchange="this.form.submit()">
          <div class="upload-icon">☁️</div>
          <div class="upload-title">Перетащи файл сюда</div>
          <div class="upload-sub">или кликни чтобы выбрать</div>
          {% if config and config.attachment_file %}<div class="file-tag">✓ {{ config.attachment_file }}</div>{% endif %}
        </div>
        <div class="hint" style="margin-top:9px">PDF, Word, картинка — любой формат</div>
      </form>
      {% if config and config.attachment_file %}
      <form method="POST" action="/remove_file" style="margin-top:9px">
        <button class="btn btn-danger" style="font-size:12px;padding:5px 12px">✕ Убрать файл</button>
      </form>
      {% endif %}
    </div>
  </div>

  <div class="section mb">
    <div class="section-title"><span class="tdot" style="background:var(--green)"></span>Запустить рассылку</div>
    <div class="grid2" style="align-items:center">
      <div>
        {% if s.today >= s.limit %}<div class="notice notice-orange">⏰ Дневной лимит ({{ s.limit }}) достигнут. Запусти завтра.</div>
        {% elif s.pending == 0 %}<div class="notice notice-green">✨ Все контакты обработаны! Добавь новые.</div>
        {% else %}<div class="notice notice-green">✓ Готово: {{ [s.limit - s.today, s.pending] | min }} контактов к отправке</div>{% endif %}
        <form method="POST" action="/run">
          <button type="submit" class="btn btn-launch" {% if s.today >= s.limit or s.pending == 0 %}disabled{% endif %}>▶ Запустить рассылку</button>
        </form>
      </div>
      <div>
        {% if s.total > 0 %}
        {% set pct = (s.sent / s.total * 100) | int %}
        <div style="font-size:11px;font-weight:600;color:var(--muted);margin-bottom:7px">Общий прогресс</div>
        <div class="progress-bar"><div class="progress-fill" style="width:{{ pct }}%"></div></div>
        <div class="progress-label"><span>{{ pct }}% завершено</span><span>{{ s.sent }} / {{ s.total }}</span></div>
        {% set tp = (s.today / s.limit * 100) | int %}
        <div style="font-size:11px;font-weight:600;color:var(--muted);margin:14px 0 7px">Сегодня</div>
        <div class="progress-bar"><div class="progress-fill" style="width:{{ tp }}%;background:linear-gradient(90deg,var(--orange),#ffd17a)"></div></div>
        <div class="progress-label"><span>{{ tp }}% лимита</span><span>{{ s.today }} / {{ s.limit }}</span></div>
        {% endif %}
      </div>
    </div>
  </div>

  <div class="section mb">
    <div class="section-title"><span class="tdot" style="background:var(--muted)"></span>Контакты {% if contacts|length > 50 %}<span style="font-size:12px;font-weight:400;color:var(--muted)">(последние 50 из {{ contacts|length }})</span>{% endif %}</div>
    {% if contacts %}
    <table>
      <thead><tr><th>#</th><th>Контакт</th><th>Имя</th><th>Статус</th></tr></thead>
      <tbody>
      {% for c in contacts[-50:] %}
      <tr>
        <td style="color:var(--muted);font-size:12px">{{ loop.index }}</td>
        <td>{{ c.phone or ('@' + c.username) }}</td>
        <td style="color:var(--muted)">{{ c.name or '—' }}</td>
        <td>{% if c.status == 'sent' %}<span class="badge b-green">✓ отправлено</span>{% elif c.status == 'failed' %}<span class="badge b-red">✗ ошибка</span>{% else %}<span class="badge b-gray">в очереди</span>{% endif %}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div style="text-align:center;color:var(--muted);padding:28px;font-size:13px">нет контактов — добавь выше 👆</div>
    {% endif %}
  </div>

  <div class="section">
    <div class="section-title"><span class="tdot" style="background:var(--muted)"></span>Управление</div>
    <div class="controls">
      <form method="POST" action="/reset_day"><button class="btn btn-ghost">🔄 Сбросить счётчик дня</button></form>
      <form method="POST" action="/retry_failed"><button class="btn btn-ghost">🔁 Повторить неудачные</button></form>
      <form method="POST" action="/edit_message"><button class="btn btn-ghost">✏️ Изменить сообщение</button></form>
      <form method="POST" action="/clear_all" onsubmit="return confirm('Сбросить весь прогресс?')"><button class="btn btn-danger">⚠️ Сбросить прогресс</button></form>
    </div>
  </div>
</div>
<script>
const zone=document.getElementById('dropZone');
if(zone){
  zone.addEventListener('dragover',e=>{e.preventDefault();zone.style.borderColor='#4a7fff';});
  zone.addEventListener('dragleave',()=>zone.style.borderColor='');
  zone.addEventListener('drop',e=>{e.preventDefault();zone.style.borderColor='';if(e.dataTransfer.files.length){document.getElementById('fileInput').files=e.dataTransfer.files;document.getElementById('uploadForm').submit();}});
}
</script>
</body>
</html>
"""

EDIT_MSG_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Изменить сообщение</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg:#eef2f7;--white:#fff;--blue:#4a7fff;--text:#2d3a52;--muted:#8a97b0;--border:#dde4f0; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }
  .box { background:var(--white); border-radius:16px; padding:32px; max-width:500px; width:100%; box-shadow:0 4px 24px rgba(74,127,255,.08); border:1px solid var(--border); }
  h1 { font-size:18px; font-weight:700; margin-bottom:20px; }
  label { display:block; font-size:12px; font-weight:600; color:var(--muted); margin-bottom:5px; }
  textarea, input { width:100%; background:var(--bg); border:1.5px solid var(--border); border-radius:10px; color:var(--text); padding:11px 13px; font-size:13px; font-family:'Inter',sans-serif; outline:none; }
  textarea { min-height:140px; resize:vertical; }
  textarea:focus, input:focus { border-color:var(--blue); background:#fff; }
  .fg { margin-bottom:14px; }
  .hint { font-size:11px; color:var(--muted); margin-top:4px; }
  .row { display:flex; gap:10px; margin-top:16px; }
  .btn { flex:1; padding:12px; border:none; border-radius:9px; font-size:13px; font-weight:600; cursor:pointer; font-family:'Inter',sans-serif; text-align:center; text-decoration:none; display:flex; align-items:center; justify-content:center; }
  .btn-blue { background:var(--blue); color:#fff; } .btn-blue:hover { background:#3a6fef; }
  .btn-gray { background:var(--bg); color:var(--muted); border:1px solid var(--border); }
</style>
</head>
<body>
<div class="box">
  <h1>✏️ Текст рассылки</h1>
  <form method="POST" action="/save_message">
    <div class="fg"><label>Текст сообщения</label><textarea name="message">{{ config.message }}</textarea><div class="hint">Используй {name} для подстановки имени контакта</div></div>
    <div class="fg"><label>Файл для прикрепления</label><input type="text" name="attachment" value="{{ config.attachment_file or '' }}" placeholder="document.pdf"></div>
    <div class="row"><a href="/" class="btn btn-gray">Отмена</a><button type="submit" class="btn btn-blue">Сохранить</button></div>
  </form>
</div>
</body>
</html>
"""

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding='utf-8') as f:
            return json.load(f)
    return None

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return []
    with open(CONTACTS_FILE, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save_contacts(contacts):
    with open(CONTACTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['phone', 'username', 'name'])
        writer.writeheader()
        writer.writerows(contacts)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"sent_today": 0, "last_date": None, "total_sent": 0, "sent_contacts": [], "failed_contacts": []}

def save_progress(p):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(p, f, indent=2, ensure_ascii=False)

def parse_line(line):
    line = line.strip()
    if not line: return None
    name = ""
    if ',' in line:
        parts = line.split(',', 1)
        identifier, name = parts[0].strip(), parts[1].strip()
    else:
        identifier = line
    if identifier.startswith('@'):
        return {'phone': '', 'username': identifier.lstrip('@'), 'name': name}
    if identifier.startswith('+') or identifier.replace(' ', '').isdigit():
        return {'phone': identifier.replace(' ', ''), 'username': '', 'name': name}
    return None

def get_stats():
    contacts_raw = load_contacts()
    progress = load_progress()
    today = str(date.today())
    if progress.get("last_date") != today:
        progress["sent_today"] = 0
        progress["last_date"] = today
        save_progress(progress)
    sent_set = set(progress.get("sent_contacts", []))
    failed_set = set(progress.get("failed_contacts", []))
    pending = len([c for c in contacts_raw if (c.get('phone') or c.get('username')) not in (sent_set | failed_set)])
    return {"total": len(contacts_raw), "sent": len(sent_set), "failed": len(failed_set),
            "pending": pending, "today": progress["sent_today"], "limit": 25}

def get_contacts_with_status():
    contacts_raw = load_contacts()
    progress = load_progress()
    sent_set = set(progress.get("sent_contacts", []))
    failed_set = set(progress.get("failed_contacts", []))
    result = []
    for c in contacts_raw:
        identifier = c.get('phone') or c.get('username', '')
        c['status'] = 'sent' if identifier in sent_set else ('failed' if identifier in failed_set else 'pending')
        result.append(c)
    return result

_flash = None

def set_flash(msg, ok=True):
    global _flash
    _flash = {"msg": msg, "cls": "flash-ok" if ok else "flash-err"}

@app.route('/')
def index():
    global _flash
    config = load_config()
    if not config: return redirect('/first_run')
    f = _flash; _flash = None
    return render_template_string(MAIN_HTML, s=get_stats(), contacts=get_contacts_with_status(), config=config, flash=f)

@app.route('/first_run')
def first_run():
    return render_template_string(SETUP_HTML, error=None, form={})

@app.route('/setup', methods=['POST'])
def setup():
    api_id = request.form.get('api_id', '').strip()
    api_hash = request.form.get('api_hash', '').strip()
    message = request.form.get('message', '').strip()
    attachment = request.form.get('attachment', '').strip()
    form = {'api_id': api_id, 'api_hash': api_hash, 'message': message, 'attachment': attachment}
    if not api_id.isdigit(): return render_template_string(SETUP_HTML, error="API ID должен быть числом", form=form)
    if len(api_hash) < 10: return render_template_string(SETUP_HTML, error="API Hash слишком короткий", form=form)
    if not message: return render_template_string(SETUP_HTML, error="Введи текст сообщения", form=form)
    config = {"api_id": int(api_id), "api_hash": api_hash, "message": message, "attachment_file": attachment,
              "session_name": "my_session", "daily_limit": 25, "batch_size": 5, "pause_minutes": 5, "pause_seconds": 10}
    save_config(config)
    set_flash("✓ Настройки сохранены! Добавь контакты и запусти рассылку.")
    return redirect('/')

@app.route('/add', methods=['POST'])
def add_contacts():
    text = request.form.get('contacts', '')
    contacts = load_contacts()
    existing = set(c.get('phone') or c.get('username') for c in contacts)
    added = 0
    for line in text.strip().split('\n'):
        c = parse_line(line)
        if c:
            identifier = c['phone'] or c['username']
            if identifier and identifier not in existing:
                contacts.append(c); existing.add(identifier); added += 1
    save_contacts(contacts)
    set_flash(f"✓ Добавлено контактов: {added}" if added else "Новых контактов не найдено (возможно дубли)")
    return redirect('/')

@app.route('/run', methods=['POST'])
def run():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sender.py')
    subprocess.Popen([sys.executable, script], creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
    set_flash("▶ Рассылка запущена! Откроется отдельное окно с прогрессом.")
    return redirect('/')

@app.route('/reset_day', methods=['POST'])
def reset_day():
    p = load_progress(); p['sent_today'] = 0; p['last_date'] = None; save_progress(p)
    set_flash("🔄 Счётчик дня сброшен."); return redirect('/')

@app.route('/retry_failed', methods=['POST'])
def retry_failed():
    p = load_progress(); count = len(p.get('failed_contacts', [])); p['failed_contacts'] = []; save_progress(p)
    set_flash(f"🔁 {count} неудачных контактов возвращены в очередь."); return redirect('/')

@app.route('/edit_message', methods=['POST'])
def edit_message():
    return render_template_string(EDIT_MSG_HTML, config=load_config() or {})

@app.route('/save_message', methods=['POST'])
def save_message():
    config = load_config() or {}
    config['message'] = request.form.get('message', '')
    config['attachment_file'] = request.form.get('attachment', '')
    save_config(config); set_flash("✓ Сообщение обновлено."); return redirect('/')

@app.route('/upload_file', methods=['POST'])
def upload_file():
    f = request.files.get('file')
    if not f or f.filename == '':
        set_flash("Файл не выбран.", ok=False); return redirect('/')
    filename = f.filename
    f.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename))
    config = load_config() or {}
    config['attachment_file'] = filename; save_config(config)
    set_flash(f"✓ Файл «{filename}» загружен и будет прикрепляться к рассылке."); return redirect('/')

@app.route('/remove_file', methods=['POST'])
def remove_file():
    config = load_config() or {}; config['attachment_file'] = ''; save_config(config)
    set_flash("Файл убран из рассылки."); return redirect('/')

@app.route('/clear_all', methods=['POST'])
def clear_all():
    if os.path.exists(PROGRESS_FILE): os.remove(PROGRESS_FILE)
    set_flash("Прогресс сброшен."); return redirect('/')

if __name__ == '__main__':
    import webbrowser, threading, time
    def open_browser():
        time.sleep(1.2)
        webbrowser.open('http://localhost:5000')
    threading.Thread(target=open_browser, daemon=True).start()
    print("\n  Открываю браузер... Если не открылся — зайди на http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
