import os
import asyncio
import logging
import json
from pathlib import Path

import aiohttp
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN', '').strip()
EXECUTOR_CHANNEL = int(os.getenv('EXECUTOR_CHANNEL_ID', '0'))
EXTERNAL_CHANNEL = int(os.getenv('EXTERNAL_CHANNEL_ID', '0'))
API_URL = 'https://weao.gg/api/status/exploits'
# WEAO expects its documented User-Agent. Set WEAO_USER_AGENT from current API docs.
USER_AGENT = os.getenv('WEAO_USER_AGENT', '').strip()
INTERVAL_MINUTES = 3
STATE_PATH = Path(__file__).with_name('message_ids.json')

# Fallback for WEAO data with no explicit executor category.
KNOWN_EXTERNALS = {
    'serotonin', 'matcha', 'severe', 'lumen', 'matrix hub', 'madius',
    'axis', 'photon', 'ronin', 'dx9ware v2'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('weao')
intents = discord.Intents.default()
client = discord.Client(intents=intents)


def load_ids():
    try:
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_ids(ids):
    STATE_PATH.write_text(json.dumps(ids, indent=2), encoding='utf-8')


def classification(item):
    title = str(item.get('title') or item.get('name') or '').strip()
    category = ' '.join(str(item.get(k) or '') for k in ('type', 'exploitType', 'category', 'executionType')).lower()
    platform = str(item.get('platform') or '').lower()
    if 'external' in category or 'external' in platform or item.get('isExternal') is True:
        return 'external'
    if 'executor' in category or 'internal' in category or item.get('isExternal') is False:
        return 'executor'
    return 'external' if title.lower() in KNOWN_EXTERNALS else 'executor'


def status(item):
    # Detected is independent of updateStatus. Show DETECTED first as requested.
    detected = item.get('detected') is True
    updated = item.get('updateStatus') is True
    if detected:
        return 'DETECTED'
    if updated:
        return 'UP'
    return 'DOWN'


def format_line(item):
    name = str(item.get('title') or item.get('name') or 'Unknown').replace('`', '')[:65]
    version = str(item.get('version') or '').replace('`', '')[:40]
    return f'• **{discord.utils.escape_markdown(name)}**' + (f'  · `{version}`' if version else '')


def build_embeds(items, kind):
    label = 'EXECUTORS' if kind == 'executor' else 'EXTERNALS'
    buckets = {'DETECTED': [], 'DOWN': [], 'UP': []}
    for item in items:
        if not isinstance(item, dict) or classification(item) != kind:
            continue
        buckets[status(item)].append(item)
    for value in buckets.values():
        value.sort(key=lambda x: str(x.get('title', '')).lower())

    e = discord.Embed(title=f'WEAO | {label}', color=0x5865F2,
                      description='WEAO API 기준 현재 상태 · 3분마다 자동 갱신')
    for key, emoji in (('DETECTED', '🔴'), ('DOWN', '🟠'), ('UP', '🟢')):
        lines = [format_line(x) for x in buckets[key]]
        value = '\n'.join(lines) if lines else '없음'
        # Discord embed fields: max 1024 characters. Split oversized fields.
        parts = []
        current = ''
        for line in value.split('\n'):
            if len(current) + len(line) + 1 > 1000:
                parts.append(current)
                current = ''
            current += ('\n' if current else '') + line
        if current:
            parts.append(current)
        for i, part in enumerate(parts):
            e.add_field(name=f'{emoji} {key} ({len(lines) if lines != ["없음"] else 0})' if i == 0 else f'{emoji} {key} (계속)', value=part, inline=False)
    e.set_footer(text='Source: weao.gg | DETECTED = 탐지됨 · DOWN = 업데이트 안 됨 · UP = 업데이트됨')
    return e


async def get_exploits():
    headers = {'Accept': 'application/json'}
    if USER_AGENT:
        headers['User-Agent'] = USER_AGENT
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(API_URL) as resp:
            if resp.status != 200:
                raise RuntimeError(f'WEAO HTTP {resp.status}: {(await resp.text())[:150]}')
            data = await resp.json(content_type=None)
    if isinstance(data, dict):
        data = data.get('data') or data.get('exploits') or data.get('results')
    if not isinstance(data, list):
        raise ValueError('Unexpected WEAO response structure')
    return data


async def send_or_edit(channel_id, kind, items):
    channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
    embed = build_embeds(items, kind)
    ids = load_ids()
    saved_id = ids.get(kind)
    if saved_id:
        try:
            msg = await channel.fetch_message(int(saved_id))
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            pass
    msg = await channel.send(embed=embed)
    ids[kind] = msg.id
    save_ids(ids)


@tasks.loop(minutes=INTERVAL_MINUTES)
async def refresh():
    try:
        items = await get_exploits()
        await send_or_edit(EXECUTOR_CHANNEL, 'executor', items)
        await send_or_edit(EXTERNAL_CHANNEL, 'external', items)
        logger.info('Refreshed WEAO status (%d entries)', len(items))
    except Exception:
        logger.exception('Refresh failed; existing messages kept')


@refresh.before_loop
async def before_refresh():
    await client.wait_until_ready()


@client.event
async def on_ready():
    logger.info('Logged in as %s', client.user)
    if not refresh.is_running():
        refresh.start()


if __name__ == '__main__':
    if not TOKEN or not EXECUTOR_CHANNEL or not EXTERNAL_CHANNEL:
        raise SystemExit('Set DISCORD_TOKEN, EXECUTOR_CHANNEL_ID, EXTERNAL_CHANNEL_ID in .env')
    client.run(TOKEN)
