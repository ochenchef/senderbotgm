"""
Telegram Sender — Веб-интерфейс
"""

import os
import json
import csv
import subprocess
import sys
from datetime import date
from flask import Flask, render_template_string, request, redirect, jsonify

app = Flask(__name__)

CONTACTS_FILE = "contacts.csv"
PROGRESS_FILE = "progress.json"
CONFIG_FILE = "config.json"

# ─────────────────────────────────────────────
# HTML шаблоны
# ─────────────────────────────────────────────

SETUP_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Настройка — Telegram Sender</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f0f1a; color: #e1e1e1; min-height: 100vh;
         display: flex; align-items: center; justify-content: center; padding: 20px; }
  .box { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 16px;
         padding: 40px; max-width: 560px; width: 100%; }
  h1 { font-size: 24px; color: #fff; margin-bottom: 8px; }
  .sub { color: #888; font-size: 14px; margin-bottom: 32px; line-height: 1.6; }
  .step { display: flex; gap: 12px; margin-bottom: 24px; padding: 16px;
          background: #12122a; border-radius: 10px; border: 1px solid #2a2a4a; }
  .num { width: 28px; height: 28px; background: #6c63ff; border-radius: 50%;
         display: flex; align-items: center; justify-content: center;
         font-size: 13px; font-weight: 700; flex-shrink: 0; }
  .step-text { font-size: 13px; color: #ccc; line-height: 1.6; }
  .step-text a { color: #6c63ff; }
  .form-group { margin-bottom: 16px; }
  label { display: block; color: #888; font-size: 12px; margin-bottom: 6px; }
  input, textarea { width: 100%; background: #0f0f1a; border: 1px solid #3a3a5a;
             border-radius: 8px; color: #e1e1e1; padding: 12px; font-size: 14px; }
  input:focus, textarea:focus { outline: none; border-color: #6c63ff; }
  textarea { resize: vertical; min-height: 100px; font-family: inherit; }
  .hint { color: #666; font-size: 11px; margin-top: 4px; }
  .btn { width: 100%; padding: 14px; background: #6c63ff; color: #fff;
         border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
         cursor: pointer; margin-top: 8px; }
  .btn:hover { background: #5a52e0; }
  .err { background: #3a1a1a; border: 1px solid #f87171; color: #f87171;
         border-radius: 8px; padding: 12px; margin-bottom: 16px; font-size: 13px; }
</style>
</head>
<body>
<div class="box">
  <h1>👋 Первый запуск</h1>
  <p class="sub">Нужно настроить один раз. Дальше просто нажимать кнопки.</p>

  <div class="step">
    <div class="num">1</div>
    <div class="step-text">
      Зайди на <a href="https://my.telegram.org" target="_blank">my.telegram.org</a> →
      войди своим номером → нажми <strong>"API Development Tools"</strong> →
      заполни название (любое) → получишь <strong>App api_id</strong> и <strong>App api_hash</strong>
    </div>
  </div>

  {% if error %}<div class="err">{{ error }}</div>{% endif %}

  <form method="POST" action="/setup">
    <div class="form-group">
      <label>API ID (число)</label>
      <input type="text" name="api_id" placeholder="12345678" required value="{{ form.api_id or '' }}">
    </div>
    <div class="form-group">
      <label>API Hash (длинная строка)</label>
      <input type="text" name="api_hash" placeholder="0123456789abcdef0123456789abcdef" required value="{{ form.api_hash or '' }}">
    </div>
    <div class="form-group">
      <label>Текст рассылки</label>
      <textarea name="message" placeholder="Привет! Напиши своё сообщение здесь.&#10;&#10;Можно использовать {name} — подставится имя контакта.">{{ form.message or '' }}</textarea>
      <div class="hint">Используй {name} для подстановки имени контакта</div>
    </div>
    <div class="form-group">
      <label>Файл для прикрепления (необязательно)</label>
      <input type="text" name="attachment" placeholder="document.pdf или оставь пустым" value="{{ form.attachment or '' }}">
      <div class="hint">Положи файл в ту же папку и напиши его имя</div>
    </div>
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
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #080810;
    --surface: #0f0f1c;
    --border: #1e1e35;
    --border2: #2a2a45;
    --text: #d4d4e8;
    --muted: #5a5a7a;
    --accent: #7c6dff;
    --accent2: #a78bfa;
    --green: #34d399;
    --orange: #fbbf24;
    --red: #f87171;
    --green-bg: #0a1f15;
    --orange-bg: #1f1500;
    --red-bg: #1f0a0a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Syne', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 32px 20px;
    background-image: radial-gradient(ellipse at 20% 0%, rgba(124,109,255,0.07) 0%, transparent 60%),
                      radial-gradient(ellipse at 80% 100%, rgba(167,139,250,0.05) 0%, transparent 60%);
  }
  .wrap { max-width: 880px; margin: 0 auto; }

  /* Header */
  .header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 36px; flex-wrap: wrap; gap: 12px; }
  .logo { display: flex; align-items: center; gap: 14px; }
  .logo-icon { width: 44px; height: 44px; background: linear-gradient(135deg, var(--accent), var(--accent2));
               border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
  .logo-text h1 { font-size: 22px; font-weight: 800; color: #fff; letter-spacing: -0.5px; line-height: 1; }
  .logo-text p { font-size: 12px; color: var(--muted); margin-top: 3px; font-family: 'JetBrains Mono', monospace; }
  .header-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); text-align: right; }
  .dot { display: inline-block; width: 7px; height: 7px; background: var(--green); border-radius: 50%;
         margin-right: 6px; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

  /* Flash */
  .flash { padding: 13px 18px; border-radius: 10px; margin-bottom: 24px; font-size: 13px; font-weight: 600; }
  .flash-ok { background: var(--green-bg); border: 1px solid rgba(52,211,153,0.3); color: var(--green); }
  .flash-err { background: var(--red-bg); border: 1px solid rgba(248,113,113,0.3); color: var(--red); }

  /* Stat cards */
  .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 18px;
          position: relative; overflow: hidden; }
  .card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
  .card.c1::before { background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .card.c2::before { background: linear-gradient(90deg, var(--green), #6ee7b7); }
  .card.c3::before { background: linear-gradient(90deg, var(--orange), #fde68a); }
  .card.c4::before { background: linear-gradient(90deg, var(--red), #fca5a5); }
  .card-label { font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
                color: var(--muted); margin-bottom: 10px; font-family: 'JetBrains Mono', monospace; }
  .card-num { font-size: 36px; font-weight: 800; letter-spacing: -2px; line-height: 1; }
  .c1 .card-num { color: var(--accent2); }
  .c2 .card-num { color: var(--green); }
  .c3 .card-num { color: var(--orange); }
  .c4 .card-num { color: var(--red); }
  .card-sub { font-size: 11px; color: var(--muted); margin-top: 4px; font-family: 'JetBrains Mono', monospace; }

  /* Sections */
  .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
             padding: 24px; margin-bottom: 16px; }
  .section-head { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }
  .section-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center;
                  justify-content: center; font-size: 15px; flex-shrink: 0; }
  .icon-blue { background: rgba(124,109,255,0.15); }
  .icon-green { background: rgba(52,211,153,0.12); }
  .icon-orange { background: rgba(251,191,36,0.12); }
  .icon-red { background: rgba(248,113,113,0.12); }
  .section-head h2 { font-size: 15px; font-weight: 700; color: #fff; }

  /* Inputs */
  textarea, input[type=text] {
    width: 100%; background: var(--bg); border: 1px solid var(--border2); border-radius: 10px;
    color: var(--text); padding: 13px 14px; font-size: 13px; font-family: 'JetBrains Mono', monospace;
    transition: border-color 0.2s;
  }
  textarea { resize: vertical; min-height: 120px; }
  textarea:focus, input[type=text]:focus { outline: none; border-color: var(--accent); }
  .hint { font-size: 11px; color: var(--muted); margin-top: 6px; font-family: 'JetBrains Mono', monospace; }

  /* Buttons */
  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 10px 18px; border-radius: 9px;
         border: none; cursor: pointer; font-size: 13px; font-weight: 700; font-family: 'Syne', sans-serif;
         transition: all 0.15s; white-space: nowrap; }
  .btn-accent { background: var(--accent); color: #fff; }
  .btn-accent:hover { background: #6a5ce8; transform: translateY(-1px); }
  .btn-launch { background: linear-gradient(135deg, var(--green), #059669); color: #000;
                font-size: 15px; padding: 14px 32px; }
  .btn-launch:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(52,211,153,0.25); }
  .btn-launch:disabled { opacity: 0.35; cursor: not-allowed; transform: none; box-shadow: none; }
  .btn-ghost { background: transparent; color: var(--muted); border: 1px solid var(--border2); }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent2); }
  .btn-danger { background: transparent; color: var(--red); border: 1px solid rgba(248,113,113,0.3); }
  .btn-danger:hover { background: var(--red-bg); }

  /* File upload zone */
  .upload-zone { border: 2px dashed var(--border2); border-radius: 12px; padding: 28px 20px;
                 text-align: center; cursor: pointer; transition: all 0.2s; position: relative; }
  .upload-zone:hover, .upload-zone.dragover { border-color: var(--accent); background: rgba(124,109,255,0.05); }
  .upload-zone input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
  .upload-icon { font-size: 28px; margin-bottom: 8px; }
  .upload-title { font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px; }
  .upload-sub { font-size: 12px; color: var(--muted); }
  .upload-current { margin-top: 12px; display: inline-flex; align-items: center; gap: 6px;
                    background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.2);
                    border-radius: 6px; padding: 5px 10px; font-size: 12px; color: var(--green);
                    font-family: 'JetBrains Mono', monospace; }

  /* Two-col layout */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

  /* Notice boxes */
  .notice { border-radius: 10px; padding: 13px 16px; font-size: 13px; font-weight: 600; margin-bottom: 16px; }
  .notice-green { background: var(--green-bg); border: 1px solid rgba(52,211,153,0.25); color: var(--green); }
  .notice-orange { background: var(--orange-bg); border: 1px solid rgba(251,191,36,0.25); color: var(--orange); }

  /* Progress */
  .progress-wrap { margin-top: 4px; }
  .progress-bar { background: var(--border2); border-radius: 4px; height: 6px; overflow: hidden; }
  .progress-fill { height: 6px; border-radius: 4px; background: linear-gradient(90deg, var(--accent), var(--accent2)); transition: width 0.4s; }
  .progress-label { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted);
                    margin-top: 6px; font-family: 'JetBrains Mono', monospace; }

  /* Table */
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; font-size: 10px; letter-spacing: 0.8px; text-transform: uppercase;
       color: var(--muted); padding: 0 12px 10px; border-bottom: 1px solid var(--border); font-family: 'JetBrains Mono', monospace; }
  td { padding: 10px 12px; border-bottom: 1px solid var(--border); font-family: 'JetBrains Mono', monospace; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(124,109,255,0.04); }

  .badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px;
           border-radius: 999px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }
  .b-green { background: rgba(52,211,153,0.12); color: var(--green); border: 1px solid rgba(52,211,153,0.2); }
  .b-red { background: rgba(248,113,113,0.12); color: var(--red); border: 1px solid rgba(248,113,113,0.2); }
  .b-gray { background: rgba(90,90,122,0.15); color: var(--muted); border: 1px solid var(--border2); }

  /* Controls row */
  .controls { display: flex; gap: 10px; flex-wrap: wrap; }

  @media(max-width: 640px) {
    .cards { grid-template-columns: repeat(2, 1fr); }
    .two-col { grid-template-columns: 1fr; }
    .card-num { font-size: 28px; }
  }
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <div class="header">
    <div class="logo">
      <div class="logo-icon">📨</div>
      <div class="logo-text">
        <h1>Telegram Sender</h1>
        <p>рассылка с твоего аккаунта</p>
      </div>
    </div>
    <div class="header-meta">
      <span class="dot"></span>работает<br>
      25 в день · 5 каждые 5 мин
    </div>
  </div>

  {% if flash %}<div class="flash {{ flash.cls }}">{{ flash.msg }}</div>{% endif %}

  <!-- Stat cards -->
  <div class="cards">
    <div class="card c1">
      <div class="card-label">Всего</div>
      <div class="card-num">{{ s.total }}</div>
      <div class="card-sub">контактов</div>
    </div>
    <div class="card c2">
      <div class="card-label">Отправлено</div>
      <div class="card-num">{{ s.sent }}</div>
      <div class="card-sub">успешно</div>
    </div>
    <div class="card c3">
      <div class="card-label">Сегодня</div>
      <div class="card-num">{{ s.today }}</div>
      <div class="card-sub">из {{ s.limit }} лимита</div>
    </div>
    <div class="card c4">
      <div class="card-label">В очереди</div>
      <div class="card-num">{{ s.pending }}</div>
      <div class="card-sub">ждут отправки</div>
    </div>
  </div>

  <!-- Contacts + File upload -->
  <div class="two-col" style="margin-bottom: 16px;">

    <!-- Add contacts -->
    <div class="section">
      <div class="section-head">
        <div class="section-icon icon-blue">👥</div>
        <h2>Добавить контакты</h2>
      </div>
      <form method="POST" action="/add">
        <textarea name="contacts" placeholder="+79001234567
+79007654321, Иван
@username
@vasya, Вася Пупкин"></textarea>
        <div class="hint">по одному на строке · с именем через запятую</div>
        <div style="margin-top: 12px;">
          <button type="submit" class="btn btn-accent">Добавить</button>
        </div>
      </form>
    </div>

    <!-- File upload -->
    <div class="section">
      <div class="section-head">
        <div class="section-icon icon-orange">📎</div>
        <h2>Прикрепить файл</h2>
      </div>
      <form method="POST" action="/upload_file" enctype="multipart/form-data" id="uploadForm">
        <div class="upload-zone" id="dropZone">
          <input type="file" name="file" id="fileInput" onchange="this.form.submit()">
          <div class="upload-icon">☁️</div>
          <div class="upload-title">Перетащи файл сюда</div>
          <div class="upload-sub">или кликни чтобы выбрать</div>
          {% if config and config.attachment_file %}
          <div class="upload-current">✓ {{ config.attachment_file }}</div>
          {% endif %}
        </div>
        <div class="hint" style="margin-top: 10px;">PDF, Word, картинка — любой файл</div>
      </form>
      {% if config and config.attachment_file %}
      <form method="POST" action="/remove_file" style="margin-top: 10px;">
        <button class="btn btn-danger" style="font-size: 12px; padding: 6px 12px;">✕ Убрать файл</button>
      </form>
      {% endif %}
    </div>

  </div>

  <!-- Launch -->
  <div class="section" style="margin-bottom: 16px;">
    <div class="section-head">
      <div class="section-icon icon-green">🚀</div>
      <h2>Запустить рассылку</h2>
    </div>
    <div class="two-col" style="align-items: center;">
      <div>
        {% if s.today >= s.limit %}
        <div class="notice notice-orange">Дневной лимит ({{ s.limit }}) достигнут. Запусти завтра.</div>
        {% elif s.pending == 0 %}
        <div class="notice notice-green">Все контакты обработаны! Добавь новые.</div>
        {% else %}
        <div class="notice notice-green">Готово: {{ [s.limit - s.today, s.pending] | min }} контактов к отправке</div>
        {% endif %}
        <form method="POST" action="/run">
          <button type="submit" class="btn btn-launch" {% if s.today >= s.limit or s.pending == 0 %}disabled{% endif %}>
            ▶ Запустить рассылку
          </button>
        </form>
      </div>
      <div>
        {% if s.total > 0 %}
        {% set pct = (s.sent / s.total * 100) | int %}
        <div class="progress-wrap">
          <div class="progress-bar"><div class="progress-fill" style="width: {{ pct }}%"></div></div>
          <div class="progress-label"><span>Общий прогресс</span><span>{{ s.sent }} / {{ s.total }} · {{ pct }}%</span></div>
        </div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- Contacts table -->
  <div class="section" style="margin-bottom: 16px;">
    <div class="section-head">
      <div class="section-icon icon-blue">📋</div>
      <h2>Контакты {% if contacts|length > 50 %}<span style="color:var(--muted);font-weight:400;font-size:12px;">(последние 50 из {{ contacts|length }})</span>{% endif %}</h2>
    </div>
    {% if contacts %}
    <table>
      <thead><tr><th>#</th><th>Контакт</th><th>Имя</th><th>Статус</th></tr></thead>
      <tbody>
      {% for c in contacts[-50:] %}
      <tr>
        <td style="color:var(--muted)">{{ loop.index }}</td>
        <td>{{ c.phone or ('@' + c.username) }}</td>
        <td style="color:var(--muted)">{{ c.name or '—' }}</td>
        <td>
          {% if c.status == 'sent' %}<span class="badge b-green">✓ отправлено</span>
          {% elif c.status == 'failed' %}<span class="badge b-red">✗ ошибка</span>
          {% else %}<span class="badge b-gray">в очереди</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div style="text-align:center; color:var(--muted); padding: 32px; font-family: 'JetBrains Mono', monospace; font-size: 13px;">
      нет контактов — добавь выше 👆
    </div>
    {% endif %}
  </div>

  <!-- Controls -->
  <div class="section">
    <div class="section-head">
      <div class="section-icon icon-red">⚙️</div>
      <h2>Управление</h2>
    </div>
    <div class="controls">
      <form method="POST" action="/reset_day">
        <button class="btn btn-ghost">🔄 Сбросить счётчик дня</button>
      </form>
      <form method="POST" action="/retry_failed">
        <button class="btn btn-ghost">🔁 Повторить неудачные</button>
      </form>
      <form method="POST" action="/edit_message">
        <button class="btn btn-ghost">✏️ Изменить сообщение</button>
      </form>
      <form method="POST" action="/clear_all" onsubmit="return confirm('Сбросить весь прогресс?')">
        <button class="btn btn-danger">⚠️ Сбросить прогресс</button>
      </form>
    </div>
  </div>

</div>
<script>
  // Drag & drop
  const zone = document.getElementById('dropZone');
  if (zone) {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('dragover');
      const dt = e.dataTransfer;
      if (dt.files.length) {
        document.getElementById('fileInput').files = dt.files;
        document.getElementById('uploadForm').submit();
      }
    });
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
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #0f0f1a; color: #e1e1e1;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .box { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 16px;
         padding: 32px; max-width: 520px; width: 100%; }
  h1 { font-size: 20px; color: #fff; margin-bottom: 20px; }
  label { display: block; color: #888; font-size: 12px; margin-bottom: 6px; }
  textarea, input { width: 100%; background: #0f0f1a; border: 1px solid #3a3a5a;
                    border-radius: 8px; color: #e1e1e1; padding: 12px; font-size: 14px; font-family: inherit; }
  textarea { min-height: 150px; resize: vertical; }
  textarea:focus, input:focus { outline: none; border-color: #6c63ff; }
  .form-group { margin-bottom: 14px; }
  .hint { color: #666; font-size: 11px; margin-top: 4px; }
  .row { display: flex; gap: 10px; margin-top: 16px; }
  .btn { flex: 1; padding: 12px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
  .btn-primary { background: #6c63ff; color: #fff; }
  .btn-outline { background: transparent; color: #888; border: 1px solid #3a3a5a; }
</style>
</head>
<body>
<div class="box">
  <h1>✏️ Текст рассылки</h1>
  <form method="POST" action="/save_message">
    <div class="form-group">
      <label>Текст сообщения</label>
      <textarea name="message">{{ config.message }}</textarea>
      <div class="hint">Используй {name} для подстановки имени контакта</div>
    </div>
    <div class="form-group">
      <label>Файл для прикрепления (имя файла или пусто)</label>
      <input type="text" name="attachment" value="{{ config.attachment_file or '' }}" placeholder="document.pdf">
    </div>
    <div class="row">
      <a href="/" class="btn btn-outline" style="text-align:center; text-decoration:none;">Отмена</a>
      <button type="submit" class="btn btn-primary">Сохранить</button>
    </div>
  </form>
</div>
</body>
</html>
"""


# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────

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
    if not line:
        return None
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
    pending = len([c for c in contacts_raw
                   if (c.get('phone') or c.get('username')) not in (sent_set | failed_set)])

    return {
        "total": len(contacts_raw),
        "sent": len(sent_set),
        "failed": len(failed_set),
        "pending": pending,
        "today": progress["sent_today"],
        "limit": 25,
    }


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


# ─────────────────────────────────────────────
# Роуты
# ─────────────────────────────────────────────

_flash = None


def set_flash(msg, ok=True):
    global _flash
    _flash = {"msg": msg, "cls": "flash-ok" if ok else "flash-err"}


@app.route('/')
def index():
    global _flash
    config = load_config()
    if not config:
        return redirect('/first_run')
    f = _flash
    _flash = None
    return render_template_string(MAIN_HTML,
                                   s=get_stats(),
                                   contacts=get_contacts_with_status(),
                                   config=config,
                                   flash=f)


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

    if not api_id.isdigit():
        return render_template_string(SETUP_HTML, error="API ID должен быть числом", form=form)
    if len(api_hash) < 10:
        return render_template_string(SETUP_HTML, error="API Hash слишком короткий", form=form)
    if not message:
        return render_template_string(SETUP_HTML, error="Введи текст сообщения", form=form)

    config = {
        "api_id": int(api_id),
        "api_hash": api_hash,
        "message": message,
        "attachment_file": attachment,
        "session_name": "my_session",
        "daily_limit": 25,
        "batch_size": 5,
        "pause_minutes": 5,
        "pause_seconds": 10,
    }
    save_config(config)
    set_flash("Настройки сохранены! Теперь добавь контакты и запусти рассылку.")
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
                contacts.append(c)
                existing.add(identifier)
                added += 1
    save_contacts(contacts)
    set_flash(f"Добавлено контактов: {added}" if added else "Новых контактов не найдено (возможно дубли)")
    return redirect('/')


@app.route('/run', methods=['POST'])
def run():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sender.py')
    subprocess.Popen([sys.executable, script],
                     creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
    set_flash("Рассылка запущена! Откроется отдельное окно с прогрессом.")
    return redirect('/')


@app.route('/reset_day', methods=['POST'])
def reset_day():
    p = load_progress()
    p['sent_today'] = 0
    p['last_date'] = None
    save_progress(p)
    set_flash("Счётчик дня сброшен.")
    return redirect('/')


@app.route('/retry_failed', methods=['POST'])
def retry_failed():
    p = load_progress()
    count = len(p.get('failed_contacts', []))
    p['failed_contacts'] = []
    save_progress(p)
    set_flash(f"{count} неудачных контактов возвращены в очередь.")
    return redirect('/')


@app.route('/edit_message', methods=['POST'])
def edit_message():
    config = load_config() or {}
    return render_template_string(EDIT_MSG_HTML, config=config)


@app.route('/save_message', methods=['POST'])
def save_message():
    config = load_config() or {}
    config['message'] = request.form.get('message', '')
    config['attachment_file'] = request.form.get('attachment', '')
    save_config(config)
    set_flash("Сообщение обновлено.")
    return redirect('/')


@app.route('/upload_file', methods=['POST'])
def upload_file():
    f = request.files.get('file')
    if not f or f.filename == '':
        set_flash("Файл не выбран.", ok=False)
        return redirect('/')
    filename = f.filename
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    f.save(save_path)
    # Автоматически прописываем файл в конфиг
    config = load_config() or {}
    config['attachment_file'] = filename
    save_config(config)
    set_flash(f"Файл «{filename}» загружен и будет прикрепляться к рассылке.")
    return redirect('/')


@app.route('/upload_file', methods=['POST'])
def upload_file():
    f = request.files.get('file')
    if not f or f.filename == '':
        set_flash("Файл не выбран.", ok=False)
        return redirect('/')
    filename = f.filename
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    f.save(save_path)
    config = load_config() or {}
    config['attachment_file'] = filename
    save_config(config)
    set_flash(f"Файл «{filename}» загружен и будет прикрепляться к рассылке.")
    return redirect('/')


@app.route('/remove_file', methods=['POST'])
def remove_file():
    config = load_config() or {}
    config['attachment_file'] = ''
    save_config(config)
    set_flash("Файл убран из рассылки.")
    return redirect('/')


@app.route('/clear_all', methods=['POST'])
def clear_all():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    set_flash("Прогресс сброшен.")
    return redirect('/')


if __name__ == '__main__':
    import webbrowser
    import threading
    def open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open('http://localhost:5000')
    threading.Thread(target=open_browser, daemon=True).start()
    print("\n  Открываю браузер... Если не открылся — зайди на http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
