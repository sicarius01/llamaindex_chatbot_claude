#!/usr/bin/env python3
"""
통합 테스트 실행 스크립트
모든 테스트를 체계적으로 실행하고 결과를 보고합니다
"""
import sys
import os
import subprocess
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_test_module(module_path: str, description: str) -> bool:
    """
    개별 테스트 모듈 실행
    
    Args:
        module_path: 테스트 모듈 경로
        description: 테스트 설명
    
    Returns:
        성공 여부
    """
    print(f"\n{'='*60}")
    print(f" {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, module_path],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # 출력 표시
        if result.stdout:
            print(result.stdout)
        if result.stderr and 'OK' not in result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"  [ERROR] 테스트 실행 실패: {str(e)}")
        return False


def main():
    """메인 테스트 실행 함수"""
    print("\n" + "="*60)
    print(" LlamaIndex 챗봇 통합 테스트 Suite")
    print("="*60)
    
    # 테스트 모듈 정의
    test_modules = [
        ("tests/test_config_loader.py", "설정 로더 테스트"),
        ("tests/test_logger.py", "로깅 시스템 테스트"),
        ("tests/test_memory.py", "메모리 관리 테스트"),
        ("tests/test_sql_validator_standalone.py", "SQL 검증 테스트"),
        ("tests/test_md_parser_core.py", "Markdown 파서 테스트"),
        ("tests/test_schema_loader.py", "스키마 로더 테스트"),
        ("tests/test_integration.py", "통합 테스트"),
    ]
    
    # 결과 추적
    results = []
    passed = 0
    failed = 0
    
    # 각 테스트 실행
    for module_path, description in test_modules:
        if Path(module_path).exists():
            success = run_test_module(module_path, description)
            results.append((description, success))
            if success:
                passed += 1
            else:
                failed += 1
        else:
            print(f"\n[SKIP] {description} - 파일을 찾을 수 없음: {module_path}")
            results.append((description, None))
    
    # 최종 결과 요약
    print("\n" + "="*60)
    print(" 테스트 결과 요약")
    print("="*60)
    
    for description, success in results:
        if success is None:
            status = "[SKIP]"
            symbol = "⚠️"
        elif success:
            status = "[PASS]"
            symbol = "✅"
        else:
            status = "[FAIL]"
            symbol = "❌"
        
        print(f"{symbol} {status:6} {description}")
    
    print(f"\n총 테스트: {len(results)}개")
    print(f"성공: {passed}개")
    print(f"실패: {failed}개")
    print(f"건너뜀: {len([r for r in results if r[1] is None])}개")
    
    if failed == 0:
        print("\n🎉 모든 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️ {failed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())