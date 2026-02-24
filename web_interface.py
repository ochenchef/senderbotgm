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
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f0f1a; color: #e1e1e1; min-height: 100vh; padding: 24px; }
  .container { max-width: 860px; margin: 0 auto; }
  h1 { font-size: 26px; color: #fff; margin-bottom: 4px; }
  .sub { color: #666; font-size: 13px; margin-bottom: 28px; }

  .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
  .card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px; padding: 18px; }
  .card-title { color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .card-val { font-size: 30px; font-weight: 700; }
  .purple { color: #6c63ff; } .green { color: #4ade80; } .orange { color: #fb923c; } .red { color: #f87171; }

  .section { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
  .section h2 { font-size: 16px; color: #fff; margin-bottom: 16px; }

  textarea { width: 100%; background: #0f0f1a; border: 1px solid #3a3a5a; border-radius: 8px;
             color: #e1e1e1; padding: 12px; font-size: 14px; font-family: inherit;
             resize: vertical; min-height: 110px; }
  textarea:focus { outline: none; border-color: #6c63ff; }
  .hint { color: #666; font-size: 11px; margin-top: 5px; }

  .btn { display: inline-block; padding: 10px 20px; border-radius: 8px; border: none;
         cursor: pointer; font-size: 14px; font-weight: 600; }
  .btn-primary { background: #6c63ff; color: #fff; }
  .btn-primary:hover { background: #5a52e0; }
  .btn-green { background: #4ade80; color: #000; font-size: 15px; padding: 12px 28px; }
  .btn-green:hover { background: #22c55e; }
  .btn-green:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-outline { background: transparent; color: #6c63ff; border: 1px solid #6c63ff; }
  .btn-outline:hover { background: #6c63ff; color: #fff; }
  .btn-red { background: transparent; color: #f87171; border: 1px solid #f87171; }
  .btn-red:hover { background: #f87171; color: #000; }

  .progress-bar { background: #2a2a4a; border-radius: 4px; height: 8px; margin-bottom: 6px; }
  .progress-fill { background: #6c63ff; border-radius: 4px; height: 8px; transition: width 0.3s; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: #666; font-size: 11px; padding: 8px 12px; border-bottom: 1px solid #2a2a4a; }
  td { padding: 9px 12px; border-bottom: 1px solid #1a1a3a; }
  tr:hover td { background: #1f1f3a; }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
  .b-green { background: #1a3a2a; color: #4ade80; }
  .b-red { background: #3a1a1a; color: #f87171; }
  .b-gray { background: #2a2a4a; color: #888; }

  .row { display: flex; gap: 16px; align-items: flex-start; }
  .col { flex: 1; }

  .notice { background: #1a2a1a; border: 1px solid #4ade80; border-radius: 8px; padding: 12px 16px;
            font-size: 13px; color: #4ade80; margin-bottom: 16px; }
  .warning { background: #2a1a0a; border: 1px solid #fb923c; border-radius: 8px; padding: 12px 16px;
             font-size: 13px; color: #fb923c; margin-bottom: 16px; }

  .flash { padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
  .flash-ok { background: #1a3a2a; border: 1px solid #4ade80; color: #4ade80; }
  .flash-err { background: #3a1a1a; border: 1px solid #f87171; color: #f87171; }

  @media(max-width: 600px) {
    .cards { grid-template-columns: repeat(2, 1fr); }
    .row { flex-direction: column; }
  }
</style>
</head>
<body>
<div class="container">
  <h1>📨 Telegram Sender</h1>
  <p class="sub">Рассылка с твоего аккаунта · 25 контактов в день · 5 штук каждые 5 минут</p>

  {% if flash %}<div class="flash {{ flash.cls }}">{{ flash.msg }}</div>{% endif %}

  <!-- Статистика -->
  <div class="cards">
    <div class="card"><div class="card-title">Всего контактов</div><div class="card-val purple">{{ s.total }}</div></div>
    <div class="card"><div class="card-title">Отправлено</div><div class="card-val green">{{ s.sent }}</div></div>
    <div class="card"><div class="card-title">Сегодня / лимит</div><div class="card-val orange">{{ s.today }} / {{ s.limit }}</div></div>
    <div class="card"><div class="card-title">В очереди</div><div class="card-val red">{{ s.pending }}</div></div>
  </div>

  <!-- Добавить контакты -->
  <div class="section">
    <h2>➕ Добавить контакты</h2>
    <form method="POST" action="/add">
      <textarea name="contacts" placeholder="+79001234567
+79007654321, Иван Иванов
@username123
@vasya, Вася Пупкин"></textarea>
      <div class="hint">Форматы: +79001234567 | @username | номер, Имя | @user, Имя — по одному на строке</div>
      <div style="margin-top: 10px;">
        <button type="submit" class="btn btn-primary">Добавить</button>
      </div>
    </form>
  </div>

  <!-- Запуск -->
  <div class="section">
    <h2>🚀 Запуск рассылки</h2>
    <div class="row">
      <div class="col">
        {% if s.today >= s.limit %}
        <div class="warning">Дневной лимит ({{ s.limit }}) достигнут. Запусти завтра.</div>
        {% elif s.pending == 0 %}
        <div class="notice">Все контакты обработаны! Добавь новые выше.</div>
        {% else %}
        <div class="notice">Готово к запуску: {{ [s.limit - s.today, s.pending] | min }} контактов</div>
        {% endif %}
        <form method="POST" action="/run">
          <button type="submit" class="btn btn-green" {% if s.today >= s.limit or s.pending == 0 %}disabled{% endif %}>
            ▶ Запустить рассылку
          </button>
        </form>
      </div>
      <div class="col">
        {% if s.total > 0 %}
        {% set pct = (s.sent / s.total * 100) | int %}
        <div class="card-title" style="margin-bottom: 8px;">Общий прогресс</div>
        <div class="progress-bar"><div class="progress-fill" style="width: {{ pct }}%"></div></div>
        <div style="font-size: 13px; color: #888;">{{ pct }}% · {{ s.sent }} из {{ s.total }}</div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- Список контактов -->
  <div class="section">
    <h2>👥 Контакты {% if contacts|length > 50 %}(показаны последние 50 из {{ contacts|length }}){% endif %}</h2>
    {% if contacts %}
    <table>
      <thead><tr><th>#</th><th>Контакт</th><th>Имя</th><th>Статус</th></tr></thead>
      <tbody>
      {% for c in contacts[-50:] %}
      <tr>
        <td style="color:#555">{{ loop.index }}</td>
        <td>{{ c.phone or ('@' + c.username) }}</td>
        <td>{{ c.name or '—' }}</td>
        <td>
          {% if c.status == 'sent' %}<span class="badge b-green">✓ Отправлено</span>
          {% elif c.status == 'failed' %}<span class="badge b-red">✗ Ошибка</span>
          {% else %}<span class="badge b-gray">В очереди</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div style="text-align:center; color:#555; padding: 20px;">Нет контактов. Добавь выше 👆</div>
    {% endif %}
  </div>

  <!-- Настройки -->
  <div class="section">
    <h2>⚙️ Управление</h2>
    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
      <form method="POST" action="/reset_day">
        <button class="btn btn-outline">🔄 Сбросить счётчик дня</button>
      </form>
      <form method="POST" action="/retry_failed">
        <button class="btn btn-outline">🔁 Повторить неудачные</button>
      </form>
      <form method="POST" action="/edit_message">
        <button class="btn btn-outline">✏️ Изменить сообщение</button>
      </form>
      <form method="POST" action="/clear_all" onsubmit="return confirm('Сбросить весь прогресс?')">
        <button class="btn btn-red">⚠️ Сбросить всё</button>
      </form>
    </div>
  </div>
</div>
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
