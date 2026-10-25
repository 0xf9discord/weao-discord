# WEAO Discord Bot — Vercel + UptimeRobot Free

This build includes `/check/<UPTIME_PATH_SECRET>` to permit UptimeRobot free HTTP monitoring, which does not support custom headers.

## Installation
1. Deploy all project files to Vercel, with `main.py` at the repository root.
2. Configure Production environment variables: `DISCORD_TOKEN`, `EXECUTOR_CHANNEL_ID`, `EXTERNAL_CHANNEL_ID`, `WEAO_USER_AGENT`, `CRON_SECRET` (existing authenticated manual endpoint), and `UPTIME_PATH_SECRET`.
3. Generate `UPTIME_PATH_SECRET` locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Keep it private (minimum 32 characters).
4. Redeploy.
5. At UptimeRobot, create **HTTP(s)** monitor with URL `https://YOUR-PROJECT.vercel.app/check/YOUR_UPTIME_PATH_SECRET`, interval 5 minutes. Default HEAD requests work. Do not use Keyword monitoring, as it requires a body and may display content.
6. Test by visiting the URL in a private browser session; 200 JSON with `posted`/`edited` means Discord was updated. If the monitor uses HEAD, expected HTTP 204 means success.

## Security notes
- This is a compromise, NOT as private as Authorization headers. URLs may appear in UptimeRobot monitor settings, browser history, and provider/access logs. Keep monitor and logs private. Rotate the secret if exposed. Never post the full URL in chat or a public repo.
- Existing `/api/refresh` remains protected by Bearer `CRON_SECRET`.
- A URL leak enables an unauthorized party to trigger refreshes; Discord bot credentials remain server-side. For stronger authentication use a scheduler supporting custom headers (e.g. GitHub Actions) or paid UptimeRobot.
- Repeated probes, overlapping runs, or upstream outages may result in errors or duplicate messages. No exactly-once guarantee.
- UptimeRobot monitors endpoints as a side effect; this is not a job scheduler and calls may be delayed or retried.


## 상태 표시 변경

DETECTED 구분을 제거했습니다. DOWN은 🔴 빨간색, UP은 🟢 초록색으로 표시합니다. 탐지 여부와 관계없이 WEAO의 `updateStatus`만 기준으로 합니다. Vercel 재배포 후 기존 UptimeRobot 설정은 그대로 사용하세요.
