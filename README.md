# 🤖 LlamaIndex + Ollama 로컬 LLM 챗봇

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-Latest-green.svg)](https://www.llamaindex.ai/)
[![Ollama](https://img.shields.io/badge/Ollama-Local-orange.svg)](https://ollama.ai/)

사내 보안 환경에서 동작하는 **완전 로컬 LLM 기반 데이터베이스 조회 챗봇**

## ✨ 주요 기능

- 🔒 **완전 로컬 실행** - 외부 API 의존성 없음
- 🚀 **LlamaIndex RAG** - 벡터 검색 기반 정보 검색
- 🛡️ **SQL 보안** - 읽기 전용 쿼리만 허용
- 💬 **대화형 인터페이스** - Rich 기반 CLI UI
- 📚 **동적 스키마** - Markdown에서 자동 로딩

## 🚀 빠른 시작

### 1. 요구사항

- Python 3.12+
- [Ollama](https://ollama.ai/) 설치
- 8GB+ RAM (권장: 16GB)

### 2. 설치

```bash
# 저장소 클론
git clone [repository-url]
cd llamaindex_chatbot_claude

# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 패키지 설치
pip install -r requirements.txt
```

### 3. Ollama 설정

```bash
# Ollama 모델 다운로드
ollama pull qwen3:4b              # LLM 모델 (4GB)
ollama pull nomic-embed-text      # 임베딩 모델 (300MB)

# Ollama 서버 시작
ollama serve
```

### 4. 실행

```bash
# 대화형 모드 실행
python main.py

# Verbose 모드 (상세 로그)
python main.py -v

# 단일 쿼리 실행
python main.py -q "employees 테이블의 구조를 알려줘"

# 인덱스 재구성
python main.py --rebuild-index
```

## 💬 사용 예시

```
You: employees 테이블에서 급여가 높은 직원 5명 조회하는 쿼리 작성해줘

Assistant: employees 테이블에서 급여가 높은 직원 5명을 조회하는 쿼리입니다:

```sql
SELECT employee_id, first_name, last_name, salary, job_title
FROM employees
ORDER BY salary DESC
LIMIT 5;
```

You: 이 결과를 부서별로 그룹화해서 보여줘

Assistant: 부서별로 그룹화하여 평균 급여와 직원 수를 보여드리겠습니다:

```sql
SELECT 
    d.department_name,
    COUNT(e.employee_id) as employee_count,
    AVG(e.salary) as avg_salary,
    MAX(e.salary) as max_salary
FROM employees e
JOIN departments d ON e.department_id = d.department_id
GROUP BY d.department_name
ORDER BY avg_salary DESC;
```
```

## 🛠️ 명령어

대화 중 사용 가능한 명령어:

| 명령어 | 설명 |
|--------|------|
| `help` | 도움말 표시 |
| `exit` / `quit` | 프로그램 종료 |
| `clear` | 대화 초기화 |
| `save [file]` | 대화 저장 |
| `load [file]` | 대화 불러오기 |
| `rebuild` | RAG 인덱스 재구축 |
| `verbose` | 상세 모드 토글 |
| `config` | 현재 설정 표시 |

## 📂 프로젝트 구조

```
├── agent/              # 핵심 Agent 모듈
│   ├── core.py        # LlamaIndex Agent
│   ├── tools.py       # RAG & SQL Tools  
│   └── memory.py      # 대화 메모리
├── parsers/           # 파서 모듈
│   ├── md_parser.py   # Markdown 파서
│   └── schema_loader.py # 동적 스키마 로더
├── data/              
│   ├── schema_docs/   # DB 스키마 (.md)
│   └── chroma_db/     # 벡터 DB
├── tests/             # 단위 테스트
├── examples/          # 예제 스크립트
└── main.py            # 진입점
```

## 📝 스키마 문서 작성

DB 스키마를 `data/schema_docs/` 폴더에 Markdown으로 작성:

```markdown
---
database: mydb
version: 1.0
---

## employees

직원 정보 테이블

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| employee_id | INT | PK | 직원 ID |
| first_name | VARCHAR(50) | | 이름 |
| department_id | INT | FK | 부서 ID |

FK: department_id -> departments.department_id
```

## 🧪 테스트

```bash
# 모든 테스트 실행
python run_tests.py

# 개별 테스트
python tests/test_schema_loader.py

# 통합 테스트  
python tests/test_integration.py
```

## ⚙️ 설정

`config.yaml` 주요 설정:

```yaml
ollama:
  model: "qwen3:4b"        # LLM 모델
  temperature: 0.7          # 생성 온도
  
vector_store:
  path: "./data/chroma_db"  # 벡터 DB 경로
  
agent:
  verbose: true             # 상세 로그
  max_context_messages: 5  # 컨텍스트 크기
  
sql:
  allow_write: false        # 항상 false (보안)
```

## 🔒 보안

- ✅ **읽기 전용 SQL** - SELECT/SHOW/DESCRIBE만 허용
- ❌ **쓰기 차단** - INSERT/UPDATE/DELETE/DROP 차단
- ❌ **Injection 방어** - 다중 쿼리 및 주입 패턴 차단
- ✅ **로컬 실행** - 외부 네트워크 접근 없음

## 🐛 문제 해결

### Ollama 연결 실패
```bash
# Ollama 상태 확인
curl http://localhost:11434/api/tags

# 모델 확인
ollama list
```

### ChromaDB 오류
```bash
# DB 초기화
rm -rf data/chroma_db
python main.py --rebuild-index
```

### Windows 인코딩 문제
자동으로 UTF-8로 처리됨 (main.py에서 설정)

## 📚 추가 문서

- [프로젝트 상세 문서](PROJECT.md)
- [개발 지시사항](CLAUDE.md)
- [예제 스크립트](examples/README.md)

## 📄 라이센스

내부 사용 전용 - 외부 공개 금지

---

*개발: AI Assistant (Claude) | 최종 업데이트: 2024.12*