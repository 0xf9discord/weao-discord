# WEAO Discord status updater

## Vercel 배포 오류 해결
- `main.py`를 ZIP 최상위에 배치했으므로 Vercel Flask 진입점으로 인식됩니다.
- Vercel 프로젝트 Root Directory를 저장소 루트로 지정하세요 (하위 폴더가 아니라 `main.py`가 있는 폴더).
- Settings > Environment Variables: DISCORD_TOKEN, EXECUTOR_CHANNEL_ID, EXTERNAL_CHANNEL_ID, WEAO_USER_AGENT, CRON_SECRET.
- 배포 후 `/`는 준비 상태를 반환합니다. 이것만으로 정기 업데이트가 실행되는 것은 아닙니다.
- 수동 실행 (비밀키를 공개하지 마세요): `curl -H "Authorization: Bearer YOUR_CRON_SECRET" https://YOUR_PROJECT.vercel.app/api/refresh`

## 무료 5분 자동 업데이트: GitHub Actions
- 이 파일들을 GitHub 저장소 루트에 올립니다.
- Settings > Secrets and variables > Actions > New repository secret 에 DISCORD_TOKEN, EXECUTOR_CHANNEL_ID, EXTERNAL_CHANNEL_ID, WEAO_USER_AGENT 등록.
- Actions에서 `Update WEAO status` 워크플로 활성화 후 `Run workflow`를 눌러 첫 실행.
- 이후 약 5분 간격 예약 실행 (GitHub 스케줄 지연/누락 가능). Vercel 배포는 필요 없습니다.
- GitHub Actions는 저장소의 기본 브랜치에 워크플로가 있어야 예약 실행됩니다.

## 참고
- WEAO가 문서에 요구하는 정확한 User-Agent를 설정해야 합니다.
- 채널 보기/메시지 읽기/전송/Embed Links 권한을 부여하세요.
- 기존 상태 메시지는 해당 봇이 작성했고 최근 100개 메시지 안에 있을 때 수정합니다.
- 실행기/익스터널 구분은 WEAO 제공 필드 및 일부 이름을 바탕으로 한 휴리스틱입니다. WEAO 데이터 구조에 따라 조정할 수 있습니다.
- DETECTED는 별도 탐지 플래그이지만 이 표시 방식에서는 DETECTED를 우선 분류합니다.
- Vercel Hobby 예약 실행은 하루 1회로 제한되므로 3분 자동화에는 적합하지 않습니다.
