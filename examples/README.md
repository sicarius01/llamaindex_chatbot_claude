# 예제 및 테스트 스크립트

이 디렉토리는 LlamaIndex 챗봇의 다양한 사용 예제와 테스트 스크립트를 포함합니다.

## 📁 파일 구조

### 기본 테스트
- `test_ollama_direct.py` - Ollama API 직접 호출 테스트
- `test_simple_agent.py` - 간단한 에이전트 동작 테스트

### 통합 테스트
- `test_ollama_integration.py` - Ollama와 LlamaIndex 통합 테스트
- `test_agent_api.py` - Agent API 기능 테스트
- `test_agent_final.py` - 최종 Agent 구현 테스트

### 전체 시스템 테스트
- `test_final.py` - 전체 시스템 통합 테스트
- `test_ollama_final.py` - Ollama 최종 통합 테스트
- `test_main_clean.py` - 메인 CLI 인터페이스 테스트

## 🚀 실행 방법

### 개별 테스트 실행
```bash
python examples/test_simple_agent.py
```

### Ollama 연결 테스트
```bash
python examples/test_ollama_direct.py
```

### 전체 시스템 테스트
```bash
python examples/test_final.py
```

## ⚠️ 주의사항

- 테스트 실행 전 Ollama 서버가 실행 중이어야 합니다
- `config.yaml` 설정이 올바르게 구성되어 있어야 합니다
- 가상환경(`.venv`)이 활성화되어 있어야 합니다

## 📋 테스트 체크리스트

- [ ] Ollama 서버 연결
- [ ] LlamaIndex Agent 초기화
- [ ] RAG 검색 기능
- [ ] SQL 쿼리 검증
- [ ] 메모리 관리
- [ ] CLI 인터페이스