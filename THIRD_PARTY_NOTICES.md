# Third-Party Notices

SpeakUp은 MIT 라이선스로 배포되며, 아래 오픈소스 소프트웨어를 사용합니다.
각 소프트웨어는 해당 라이선스 조건을 따릅니다.

## Frontend (apps/web)

| 패키지 | 라이선스 | 용도 |
|---|---|---|
| [@mediapipe/tasks-vision](https://github.com/google-ai-edge/mediapipe) | Apache-2.0 | 시선·자세·표정·제스처 landmark 추출 |
| [three](https://github.com/mrdoob/three.js) | MIT | 3D 렌더링 |
| [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) | MIT | VRM 아바타 로딩/리타게팅 |
| [zod](https://github.com/colinhacks/zod) | MIT | 런타임 스키마 검증 |
| [vite](https://github.com/vitejs/vite) | MIT | 빌드 도구 (dev) |
| [typescript](https://github.com/microsoft/TypeScript) | Apache-2.0 | 언어/컴파일러 (dev) |

## Backend (services/*)

| 패키지 | 라이선스 | 용도 |
|---|---|---|
| [FastAPI](https://github.com/fastapi/fastapi) | MIT | API 서버 |
| [uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI 서버 |
| [pydantic](https://github.com/pydantic/pydantic) | MIT | 데이터 검증/스키마 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | 로컬 STT |
| [librosa](https://github.com/librosa/librosa) | ISC | prosody(운율) 분석 |
| [soundfile](https://github.com/bastibe/python-soundfile) | BSD-3-Clause | 오디오 I/O |
| [psycopg](https://github.com/psycopg/psycopg) | LGPL-3.0 | PostgreSQL 드라이버 (라이브러리로만 사용, 수정 없음) |
| [httpx](https://github.com/encode/httpx) | BSD-3-Clause | 서비스 간 HTTP 클라이언트 |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | rubric YAML 파싱 |
| [openai (SDK)](https://github.com/openai/openai-python) | Apache-2.0 | OpenAI 호환 LLM/STT API 클라이언트 |
| [google-genai (SDK)](https://github.com/googleapis/python-genai) | Apache-2.0 | Gemini API 클라이언트 |
| [anthropic (SDK)](https://github.com/anthropics/anthropic-sdk-python) | MIT | Claude API 클라이언트 |
| [python-multipart](https://github.com/Kludex/python-multipart) | Apache-2.0 | 파일 업로드 파싱 |

## 시스템 구성요소 (Docker 이미지 내)

| 소프트웨어 | 라이선스 | 용도 |
|---|---|---|
| [PostgreSQL 16](https://www.postgresql.org/about/licence/) | PostgreSQL License | 데이터 저장 |
| [FFmpeg](https://ffmpeg.org/legal.html) | LGPL-2.1+ (Debian 빌드) | 오디오 추출, MP4 변환 — 별도 프로세스로 호출하며 링크하지 않음 |
| [Python 3.11 (python:3.11-slim)](https://docs.python.org/3/license.html) | PSF-2.0 | 백엔드 런타임 |

## 브라우저 내장 API

Web Speech API, MediaRecorder, WebSocket 등 브라우저 표준 API는 별도 라이선스
고지 대상이 아닙니다.

## 에셋

- `apps/web/public/avatars/default.vrm`: 샘플 VRM 아바타.
  <!-- TODO: 아바타 출처와 이용약관(재배포 허용 여부)을 확인하여 여기에 기재할 것.
       재배포가 허용되지 않는 모델이라면 저장소에서 제거하고 다운로드 안내로 대체. -->

## 외부 API 서비스

전북 AI 학생 API, Google Gemini API, Anthropic Claude API는 소프트웨어 배포물이
아닌 외부 서비스이며, 각 서비스 약관에 따라 사용자가 직접 API 키를 발급받아
사용합니다. API 키는 저장소에 포함되지 않습니다.
