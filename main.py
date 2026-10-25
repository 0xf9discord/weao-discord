"""WEAO Discord status updater: Vercel Flask endpoint or GitHub Actions one-shot."""
import os
import sys
import logging
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
API = 'https://weao.gg/api/status/exploits'
DISCORD_API = 'https://discord.com/api/v10'
EXTERNALS = {'serotonin', 'matcha', 'severe', 'lumen', 'matrix hub', 'madius', 'axis', 'photon', 'ronin', 'dx9ware v2'}


def require_env(key):
    value = os.environ.get(key, '').strip()
    if not value or value.startswith('YOUR_'):
        raise RuntimeError(f'Missing environment variable: {key}')
    return value


def call_discord(method, path, **kwargs):
    token = require_env('DISCORD_TOKEN')
    response = requests.request(method, DISCORD_API + path, headers={
        'Authorization': f'Bot {token}', 'User-Agent': 'DiscordBot (https://discord.com, 1.0)',
    }, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def fetch_statuses():
    agent = require_env('WEAO_USER_AGENT')
    r = requests.get(API, headers={'User-Agent': agent, 'Accept': 'application/json'}, timeout=25)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        data = data.get('data') or data.get('exploits') or data.get('results')
    if not isinstance(data, list):
        raise RuntimeError('WEAO returned unexpected JSON')
    return data


def group(item):
    name = str(item.get('title') or item.get('name') or '').lower().strip()
    fields = ' '.join(str(item.get(k) or '') for k in ('type', 'exploitType', 'category', 'executionType', 'platform')).lower()
    if item.get('isExternal') is True or 'external' in fields:
        return 'external'
    if item.get('isExternal') is False or 'executor' in fields or 'internal' in fields:
        return 'executor'
    return 'external' if name in EXTERNALS else 'executor'


def state(item):
    if item.get('detected') is True:
        return 'DETECTED'
    if item.get('updateStatus') is True:
        return 'UP'
    return 'DOWN'


def make_embed(items, kind):
    groups = {'DETECTED': [], 'DOWN': [], 'UP': []}
    for item in items:
        if isinstance(item, dict) and group(item) == kind:
            name = str(item.get('title') or item.get('name') or 'Unknown')[:80].replace('`', '')
            groups[state(item)].append(name)
    fields = []
    for st, emoji in [('DETECTED', '🔴'), ('DOWN', '🟠'), ('UP', '🟢')]:
        names = sorted(groups[st], key=str.casefold)
        chunks = []
        current = ''
        for name in names:
            line = '• ' + name.replace('*', '\\*').replace('_', '\\_')
            if len(current) + len(line) + 1 > 990:
                chunks.append(current)
                current = ''
            current += ('\n' if current else '') + line
        chunks.append(current or '없음')
        for i, part in enumerate(chunks):
            fields.append({'name': f'{emoji} {st} ({len(names)})' if i == 0 else f'{emoji} {st} (계속)', 'value': part, 'inline': False})
    # Discord embed max 25 fields, 6000 characters overall.
    if len(fields) > 25:
        raise RuntimeError('Too many entries for one embed')
    return {'title': f'WEAO | {"EXECUTORS" if kind == "executor" else "EXTERNALS"}',
            'description': 'WEAO API 기준 · 자동 상태 갱신', 'color': 0x5865F2,
            'fields': fields, 'footer': {'text': 'DETECTED=탐지 · DOWN=미업데이트 · UP=업데이트'},
            'timestamp': datetime.now(timezone.utc).isoformat()}


def update_channel(channel_id, kind, items):
    embed = make_embed(items, kind)
    # No local state files: safe in serverless. Find a recent message posted by this bot.
    myself = call_discord('GET', '/users/@me')['id']
    messages = call_discord('GET', f'/channels/{channel_id}/messages?limit=100')
    existing = next((m for m in messages if str(m.get('author', {}).get('id')) == str(myself)
                     and any(e.get('title') == embed['title'] for e in m.get('embeds', []))), None)
    if existing:
        call_discord('PATCH', f'/channels/{channel_id}/messages/{existing["id"]}', json={'embeds': [embed]})
        return 'edited'
    call_discord('POST', f'/channels/{channel_id}/messages', json={'embeds': [embed]})
    return 'posted'


def update_all():
    items = fetch_statuses()
    return {'executor': update_channel(require_env('EXECUTOR_CHANNEL_ID'), 'executor', items),
            'external': update_channel(require_env('EXTERNAL_CHANNEL_ID'), 'external', items),
            'items': len(items)}


@app.get('/')
def home():
    return jsonify({'status': 'ready', 'service': 'WEAO Discord updater', 'manual_refresh': '/api/refresh'})


@app.get('/api/refresh')
def refresh():
    secret = os.getenv('CRON_SECRET', '')
    if not secret or request.headers.get('Authorization') != f'Bearer {secret}':
        return jsonify({'error': 'unauthorized'}), 401
    try:
        return jsonify(update_all())
    except Exception:
        app.logger.exception('Update error')
        return jsonify({'error': 'Update failed; see Vercel function logs'}), 500


if __name__ == '__main__':
    if '--once' in sys.argv:
        print(update_all())
    else:
        app.run(port=5000)
