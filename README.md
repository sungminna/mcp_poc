# react-mcp

**react-mcp**는 FastAPI 기반의 백엔드 애플리케이션으로, LLM(REACT 에이전트), 지식 그래프(Neo4j), 벡터 스토어(Milvus), PostgreSQL, Redis를 통합하여 개인화된 대화형 챗봇 서비스를 제공합니다.

---

## 📚 프로젝트 개요

- **대화형 REACT 챗봇**: 사용자의 질의에 대해 LangGraph의 REACT 에이전트를 활용하여 응답을 생성합니다.
- **지식 그래프 연동**: Neo4j에 저장된 사용자 정보 및 관계 데이터를 기반으로 대화 컨텍스트를 보강합니다.
- **벡터 검색**: Milvus를 사용하여 OpenAI 임베딩을 저장하고, 유사도 검색을 통해 관련 정보를 조회합니다.
- **구조화된 개인 정보 추출**: 사용자의 발화에서 키워드를 추출하고, JSON 형태로 파싱하여 Neo4j에 저장합니다.
- **인증 및 권한**: JWT 기반 로그인/회원가입, 비밀번호 해싱(bcrypt)을 통한 보안 기능 제공.
- **비동기 처리**: FastAPI와 SQLAlchemy AsyncSession, AsyncIO를 활용한 고성능 비동기 아키텍처.
- **레이트 리미팅**: `slowapi`를 활용하여 엔드포인트별 요청 횟수를 제어합니다.
- **로깅 및 트레이싱**: Python `logging`과 Langfuse 콜백을 통해 요청별 트레이싱 및 로깅을 수행합니다.

---

## 🔨 기술 스택 및 주요 라이브러리

| 구분            | 라이브러리/도구                     |
| -------------- | ---------------------------------- |
| 프레임워크       | FastAPI, Uvicorn                   |
| 데이터베이스     | PostgreSQL (asyncpg), SQLAlchemy   |
| 지식 그래프      | Neo4j (neo4j-driver)              |
| 벡터 스토어      | Milvus (pymilvus)                  |
| 캐싱            | Redis (aioredis)                   |
| 인증/보안        | python-jose, passlib[bcrypt], bcrypt|
| LLM & 에이전트   | langchain, langgraph, langchain-openai |
| 트레이싱        | langfuse                           |
| 레이트 리미팅    | slowapi                            |
| 환경 변수 관리   | python-dotenv                      |
| 개발 및 배포     | Poetry, Docker                     |
| 프론트엔드       | SvelteKit, Vite, TypeScript, CSS    |

---

## 📂 디렉토리 구조

```
react_mcp/
├── main.py                 # 애플리케이션 진입점 및 라이프사이클 관리
├── database.py             # SQLAlchemy 비동기 엔진 및 세션 설정
├── core/                   # 공통 설정 및 보안 모듈
│   ├── config.py           # 환경 변수 및 설정
│   └── security.py         # JWT 생성, 검증, 비밀번호 해싱
├── routers/                # API 라우터 정의
│   ├── auth.py             # 로그인(Token 발급)
│   ├── users.py            # 사용자 CRUD
│   ├── general.py          # 기본 헬로 월드 테스트 엔드포인트
│   └── ask.py              # 챗봇 대화 흐름 (세션 관리, LLM 호출 등)
├── services/               # 외부 서비스 연동 모듈
│   ├── neo4j_service.py    # Neo4j 연결, 노드/관계 생성, 유사 정보 검색, 임베딩 워크플로우
│   ├── milvus_service.py   # Milvus 컬렉션/인덱스 관리, 벡터 삽입/검색
│   └── llm_service.py      # REACT 에이전트 초기화 및 질문 처리
├── crud/                   # 데이터베이스 CRUD 함수
│   ├── user.py             # User 모델 CRUD
│   └── chat.py             # Chat 세션/메시지 CRUD
├── models/                 # Pydantic 및 ORM 모델 정의
│   ├── user.py             # User, Token, UserCreate, UserResponse
│   └── chat.py             # Chat 세션, 메시지 모델
├── prompts.py              # LangChain Prompt 템플릿 정의
├── client.py               # REACT 에이전트 예제 클라이언트 스크립트
├── weather_server.py       # 예제 외부 도구(날씨) 서버
├── math_server.py          # 예제 외부 도구(계산) 서버
├── pyproject.toml          # 프로젝트 설정 및 의존성
├── Dockerfile              # Docker 이미지 빌드 스크립트
└── README.md               # 프로젝트 설명 (이 파일)
```

## 📂 전체 디렉토리 구조
```
프로젝트 루트/
├── react_mcp/               # FastAPI 백엔드
│   └── ...                  # (생략)
├── velt/                    # SvelteKit 프론트엔드
│   └── src/
│       ├── app.html         # 글로벌 HTML 템플릿
│       ├── app.css          # 글로벌 CSS 스타일
│       ├── app.d.ts         # 타입 정의
│       ├── routes/          # 페이지 라우팅
│       └── lib/             # 공용 컴포넌트 및 유틸리티
└── README.md                # 프로젝트 설명
```

---

## 🚀 설치 및 실행

1. Python 3.13 설치
2. Poetry 설치 및 의존성 설치
   ```bash
   cd react_mcp
   poetry install
   ```
3. `.env` 파일 생성 및 필수 환경 변수 설정 (아래 참조)
4. 개발 서버 실행
   ```bash
   poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker

```bash
# 이미지 빌드
docker build -t react-mcp .
# 컨테이너 실행
docker run -d -p 8000:8000 --env-file .env react-mcp
```

---

## ⚙️ 환경 변수

| 변수명                    | 설명                                            | 기본값/예시                                   |
| ------------------------- | ----------------------------------------------- | --------------------------------------------- |
| SECRET_KEY                | JWT 서명 및 검증 키                              | 없음 (반드시 설정)                           |
| DATABASE_URL              | PostgreSQL 연결 URL                             | postgresql+asyncpg://user:pw@host:port/dbname |
| NEO4J_URI                 | Neo4j Bolt URI                                   | bolt://localhost:7687                        |
| NEO4J_USER                | Neo4j 사용자명                                   | neo4j                                        |
| NEO4J_PASSWORD            | Neo4j 비밀번호                                   | password                                     |
| MILVUS_HOST               | Milvus 호스트                                    | localhost                                    |
| MILVUS_PORT               | Milvus 포트                                      | 19530                                        |
| REDIS_URL                 | Redis 연결 URL                                   | redis://localhost:6379                       |
| LANGFUSE_SECRET_KEY       | Langfuse 비공개 키                               | -                                            |
| LANGFUSE_PUBLIC_KEY       | Langfuse 공개 키                                 | -                                            |
| LANGFUSE_HOST             | Langfuse 서버 호스트                             | http://localhost:3000                        |
| RATE_LIMIT_CHAT           | 챗봇 요청 레이트 제한 (e.g., "30/minute")      | 30/minute                                    |
| RATE_LIMIT_LOGIN          | 로그인 요청 레이트 제한 (e.g., "10/minute")    | 10/minute                                    |
| RATE_LIMIT_REGISTER       | 회원가입 요청 레이트 제한 (e.g., "5/hour")     | 5/hour                                       |
| CORS_ALLOW_ORIGINS        | 허용할 CORS 오리진 (콤마 구분)                   | *                                            |

---

## 🔗 주요 API 엔드포인트

### 인증 (Auth)
- **POST /api/auth/token**: 로그인 및 액세스 토큰(JWT) 발급

### 사용자 (Users)
- **POST /api/users/**: 회원가입
- **GET /api/users/me**: 토큰 기반 현재 사용자 정보 조회
- **GET /api/users/{user_id}**: 특정 사용자 조회
- **GET /api/users/**: 사용자 목록 조회 (인증 필요)

### 챗봇 (Chat)
- **POST /api/chat/**: 챗 메시지 전송 → LLM 응답 반환
- **GET /api/chat/sessions**: 대화 세션 목록 조회
- **GET /api/chat/{session_id}/messages**: 특정 세션의 메시지 조회
- **DELETE /api/chat/{session_id}**: 세션 및 메시지 삭제

### 기타
- **GET /**: 기본 헬로 월드 응답
- **GET /items/{item_id}?q=**: 테스트용 엔드포인트

---

## 🏗️ 아키텍처 및 워크플로우

1. **애플리케이션 시작** (`lifespan` 훅)
   - PostgreSQL 스키마 생성
   - Neo4j, Milvus 연결 및 인덱스/컬렉션 보장
2. **유저 흐름**
   - 회원가입 → PostgreSQL 저장 + Neo4j에 유저 노드 생성
   - 로그인 → JWT 발급
3. **챗봇 흐름**
   - 세션 조회/생성 → 과거 메시지를 메모리 컨텍스트에 로드
   - 사용자 메시지 저장 → 임시 컨텍스트에 추가
   - 키워드 추출 → Neo4j에서 유사 정보 조회 → 프롬프트 보강
   - REACT 에이전트 호출 → 최종 응답 저장 및 반환
   - 백그라운드에서 개인 정보 JSON 파싱 → Neo4j에 저장
4. **임베딩 & 벡터 검색**
   - OpenAI 임베딩 생성 (Redis 캐시)
   - Milvus에 벡터 저장 및 유사도 검색

---

## 📄 라이선스

MIT License

---

## ✉️ 문의 및 기여

- 작성자: sungminna (sungmin.na330@gmail.com)
- 기여 환영합니다! 이슈 및 PR을 통해 자유롭게 의견을 나눠주세요.

## 📱 프론트엔드 (SvelteKit)

**velte** 디렉토리 안에 SvelteKit 기반 프론트엔드 애플리케이션이 위치합니다.

- 구조
  - `src/routes/`: SvelteKit의 페이지 및 API 라우팅 엔드포인트
  - `src/lib/`: 공용 컴포넌트, 유틸리티 및 데이터 모델
  - `app.html`: 전체 페이지에 적용되는 HTML 템플릿
  - `app.css`: 글로벌 스타일 시트
  - `app.d.ts`: 전역 타입 정의
- Vite 설정: `svelte.config.js`에서 `vitePreprocess()` 및 `@sveltejs/adapter-auto` 사용

### 실행 방법
```bash
cd velt
npm install
npm run dev
```

### 빌드 및 배포
```bash
cd velt
npm run build
npm run preview
```
