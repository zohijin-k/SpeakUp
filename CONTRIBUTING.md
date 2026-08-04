# Contributing to SpeakUp

SpeakUp에 관심 가져주셔서 감사합니다. 버그 리포트, 기능 제안, 코드 기여, 새로운
코칭 시나리오(rubric) 추가 모두 환영합니다.

## 개발 환경 준비

사전 요구사항: Docker Desktop, Node.js 20.19+ / 22.12+, Chrome (데스크톱)

```bash
git clone https://github.com/zohijin-k/SpeakUp.git
cd SpeakUp
cp .env.example .env   # LLM/STT API 키 설정 (Gemini 무료 키만으로도 동작)

# 백엔드
docker compose up -d postgres audio aggregator coach

# 프론트엔드 (개발 서버)
cd apps/web
npm install
npm run dev            # http://localhost:5173
```

Docker의 audio 서비스로 정적 웹을 서빙하려면 `npm run build`를 먼저 실행하세요.
빌드 결과물(`services/audio-pipeline/app/static/`)은 저장소에 커밋하지 않습니다.

## 가장 쉬운 기여: 코칭 시나리오(rubric) 추가

SpeakUp의 코칭 시나리오는 `services/coach/rubrics/*.yaml`에 정의되어 있습니다.
코드를 몰라도 YAML 파일 하나로 새로운 연습 상황(예: 스터디 발표, 전화 상담,
학회 질의응답)을 추가할 수 있습니다.

1. 기존 파일(예: `presentation.yaml`)을 복사해 새 시나리오 이름으로 저장
2. 평가 항목, 가중치, 코칭 문구 톤을 상황에 맞게 수정
3. PR을 열고 시나리오의 목적과 대상 사용자를 설명

## 브랜치와 PR 규칙

- `main`은 항상 실행 가능한 상태를 유지합니다.
- 브랜치 이름: `feat/…`, `fix/…`, `docs/…`
- 커밋 메시지: 변경 의도가 드러나게 한 줄 요약 (한국어/영어 무관)
- PR은 작게, 하나의 주제로. 화면이 바뀌면 스크린샷이나 짧은 녹화를 첨부해주세요.
- CI(웹 빌드 + Python 문법 검사)가 통과해야 머지합니다.

## 버그 리포트

이슈 템플릿을 사용해주세요. 재현 절차, 브라우저/OS, `docker compose logs`의
관련 로그가 있으면 훨씬 빨리 고칠 수 있습니다.

## 코드 스타일

- TypeScript: 기존 코드의 모듈 구조를 따릅니다 (`apps/web/src/` 하위 도메인별 폴더)
- Python: FastAPI 서비스별로 독립적인 `app/` 패키지 구조를 유지합니다
- 공유 데이터 형태를 바꿀 때는 `packages/schema/`의 Python/TypeScript 스키마를
  함께 수정해주세요.

## 라이선스

기여한 코드는 프로젝트와 동일하게 [MIT License](LICENSE)로 배포되는 것에
동의하는 것으로 간주합니다.
