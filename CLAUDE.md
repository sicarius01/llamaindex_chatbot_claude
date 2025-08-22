# Ollama + LlamaIndex 기반 로컬 LLM Agent 개발 작업지시서

## 📊 현재 구현 상태 (2024.12)

### ✅ 구현 완료
- **LlamaIndex 통합**: Ollama LLM/Embedding 모델 연동 완료
- **RAG 시스템**: ChromaDB + VectorStoreIndex 구현
- **SQL 보안**: 읽기 전용 검증, SQL Injection 방어
- **동적 스키마**: SchemaLoader로 .md 파일에서 자동 로딩
- **메모리 관리**: 세션별 대화 기록 관리
- **CLI 인터페이스**: Rich 라이브러리 기반 대화형 UI
- **테스트**: 50개+ 단위/통합 테스트

### ⚠️ 미구현/개선 필요
- **실제 DB 연결**: 현재 시뮬레이션 모드
- **성능 최적화**: SQL 검증 속도 개선 필요
- **웹 UI**: 현재 CLI만 지원

## 1. 프로젝트 개요
본 프로젝트는 사내 보안 환경에서 동작하는 **로컬 LLM 기반 챗봇 에이전트**를 개발하는 것을 목표로 한다.  
이 챗봇은 LlamaIndex를 통해 RAG 기반의 정보 검색을 수행하며, LLM은 **Ollama 로컬 인퍼런스**를 사용한다.  
최초 인터페이스는 CLI 기반으로 제작하며, 향후 프론트엔드(UI)로 확장 가능하도록 설계한다.

---

## 2. 기술 스택
- **프로그래밍 언어**: Python 3.x
- **가상환경 경로**: `./.venv` (프로젝트 루트에 위치)
- **LLM 엔진**: Ollama (로컬 서버, 예: `llama3`)
- **RAG 프레임워크**: LlamaIndex
- **벡터DB**: ChromaDB (로컬 저장)
- **데이터 포맷**: Markdown (`.md`) 문서 기반
- **실행 환경**: 사내 네트워크(인터넷 단절 가능성 있음)

---

## 3. 주요 요구사항

### 3.1 설정(config) 기반 구조
- 하드코딩 금지.  
- 모든 환경 변수 및 설정값은 **config 파일**(`config.yaml` 또는 `.json`)에서 로드.  
- 변경 가능한 설정 예시:
  - Ollama 서버 주소 및 포트
  - Ollama 모델명
  - ChromaDB 저장소 경로
  - 데이터(Markdown) 파일 경로
  - Agent 동작 관련 옵션 (예: verbose 여부, 응답 최대 토큰 수 등)

### 3.2 DB 조회 정책
- DB 관련 질의 시 **SELECT/조회만 허용**.
- 어떠한 경우에도 **INSERT/UPDATE/DELETE/ALTER 등 데이터 변경 금지**.
- SQL 실행 모듈에서 쿼리를 사전 검사하여, 변경 쿼리 발견 시 실행 거부 및 경고 로그 출력.

### 3.3 데이터 로딩
- 사내에서 제공한 **Markdown 파일**(`.md`)에 DB 테이블 스키마 정보 포함.
- LlamaIndex가 해당 `.md` 파일을 파싱하여 검색 인덱스를 생성.
- 데이터 구조는 변경 가능성이 있으므로, Parser를 별도 모듈로 구현하여 유지보수성 확보.

### 3.4 벡터 데이터 저장
- ChromaDB 사용, 로컬 저장소 지정 가능.
- 인덱스 생성 및 검색 과정은 LlamaIndex를 통해 처리.
- 데이터 변경 시 재인덱싱 기능 제공.

### 3.5 Agent 설계
- **기본 동작**:  
  1. 사용자의 질의 입력
  2. Agent가 의도 분석
  3. 필요 시 Tool 호출:
     - RAG 검색 (문서 검색)
     - SQL 조회
  4. 검색 결과를 LLM에 전달하여 최종 답변 생성
- **메모리 기능**:  
  - 대화 컨텍스트 유지(최근 n회 발화)
  - config에서 on/off 가능
- **Ollama 연동**:
  - LlamaIndex의 Ollama LLM 클래스 사용
  - config에서 모델명, 서버 주소 지정 가능

### 3.6 CLI 인터페이스
- 텍스트 기반 대화창 제공.
- `exit` 입력 시 종료.
- Agent의 각 단계(Tool 호출, 쿼리 결과 등)를 verbose 모드에서 출력.

### 3.7 로깅
- 모든 질의/응답/Tool 호출 내용을 로그 파일로 저장.
- SQL 실행 시 실행된 쿼리와 결과를 별도로 기록.
- 오류 발생 시 스택트레이스와 함께 로그 기록.

---
## 4. 디렉토리 구조 (실제 구현)

```
project_root/
├── .venv/                   # 가상환경
├── config.yaml              # 환경설정 파일
├── main.py                  # 진입점 (CLI 인터페이스)
├── run_tests.py             # 테스트 실행 스크립트
├── agent/
│   ├── __init__.py
│   ├── core.py              # LlamaIndex Agent Core (FunctionCallingAgentWorker)
│   ├── tools.py             # Tool 정의 (RAG, SQL 조회) ✅
│   └── memory.py            # 대화 메모리 관리 ✅
├── data/
│   ├── schema_docs/         # DB 스키마 .md 파일
│   └── chroma_db/           # ChromaDB 저장소
├── parsers/
│   ├── md_parser.py         # Markdown -> LlamaIndex document 변환 ✅
│   └── schema_loader.py     # 동적 스키마 로더 (하드코딩 제거) ✅
├── utils/
│   ├── config_loader.py     # config 로드 (싱글톤 패턴) ✅
│   └── logger.py            # 로깅 유틸 ✅
├── tests/                   # 단위 테스트
├── examples/                # 예제 및 통합 테스트
├── logs/                    # 로그 파일 저장 폴더
├── requirements.txt         # 패키지 의존성
└── README.md                # 프로젝트 설명서
```

---

## 5. config.yaml 예시

```yaml
ollama:
  host: "http://localhost"
  port: 11434
  model: "llama3"

vector_store:
  type: "chromadb"
  path: "./data/chroma_db"

data:
  schema_path: "./data/schema_docs"

agent:
  verbose: true
  max_context_messages: 5

sql:
  allow_write: false

logging:
  level: "INFO"
  file: "./logs/agent.log"
## 6. 주요 구현 내용

### 6.1 LlamaIndex Agent (agent/core.py)
```python
# FunctionCallingAgentWorker 사용
from llama_index.llms.ollama import Ollama
from llama_index.core.agent import FunctionCallingAgentWorker

agent_worker = FunctionCallingAgentWorker.from_tools(
    tools=self.tools,  # RAG + SQL tools
    llm=llm,
    system_prompt=system_prompt
)
```

### 6.2 동적 스키마 로더 (parsers/schema_loader.py)
- Markdown 파일에서 테이블 정보 자동 추출
- YAML front matter 메타데이터 지원
- 하드코딩 완전 제거

### 6.3 SQL 보안 (agent/tools.py)
- SQLValidator 클래스로 모든 쿼리 검증
- WRITE_KEYWORDS 차단
- SQL Injection 패턴 감지

## 7. 개발 절차 (완료)
환경 구성

.venv 가상환경 생성 및 활성화

requirements.txt 기반 패키지 설치

Ollama 서버 준비 (ollama serve), 모델 다운로드(ollama pull llama3)

config 로더 구현

utils/config_loader.py에서 config 파일 로딩

전역 설정 객체로 전달 가능하게 설계

Markdown 파서 구현

.md 파일을 읽어 LlamaIndex Document 객체로 변환

DB 테이블명, 컬럼명, 타입, 설명 등을 추출

추출 방식은 유연하게 (향후 포맷 변경 가능성 고려)

VectorStore 생성

ChromaDB 로컬 인스턴스 생성

문서 인덱싱 기능 구현 (재인덱싱 지원)

Agent Core 구현

Ollama LLM 연결

Tool 등록 (RAG 검색, SQL 조회)

메모리 기능 적용

SQL 조회 Tool 구현

DB 연결

쿼리 실행 전 SQL문 분석 → 변경 쿼리 차단

결과 반환

CLI 인터페이스 구현

사용자 입력 → Agent 응답 출력

verbose 모드 시 중간 처리 단계 표시

로깅 구현

질의/응답, 오류, SQL 실행 로그 저장

7. 주의사항
하드코딩 금지: 모든 값은 config에서 불러오기

DB 변경 금지: SELECT 외의 쿼리는 실행 불가

보안 준수: 외부 API 호출 금지, 모든 연산은 로컬/사내 네트워크 내에서만 수행

유연한 확장성: 향후 프론트엔드/UI와의 연동, 다중 에이전트 구조 확장을 고려하여 모듈화