# 샘플 데이터베이스 스키마

Database: company_db

이 문서는 회사 데이터베이스의 스키마 정보를 포함합니다.

## Table: employees

직원 정보를 관리하는 테이블입니다. 모든 직원의 기본 정보와 부서 정보를 포함합니다.

| Column | Type | Description |
|--------|------|-------------|
| employee_id | INT PRIMARY KEY | 직원 고유 ID |
| first_name | VARCHAR(50) | 이름 |
| last_name | VARCHAR(50) | 성 |
| email | VARCHAR(100) UNIQUE | 이메일 주소 |
| phone | VARCHAR(20) | 전화번호 |
| hire_date | DATE | 입사일 |
| job_title | VARCHAR(100) | 직책 |
| salary | DECIMAL(10,2) | 급여 |
| department_id | INT | 부서 ID (FK) |
| manager_id | INT | 관리자 직원 ID |
| created_at | TIMESTAMP | 레코드 생성 시간 |
| updated_at | TIMESTAMP | 레코드 수정 시간 |

## Table: departments

부서 정보를 관리하는 테이블입니다.

| Column | Type | Description |
|--------|------|-------------|
| department_id | INT PRIMARY KEY | 부서 고유 ID |
| department_name | VARCHAR(100) | 부서명 |
| location | VARCHAR(200) | 부서 위치 |
| budget | DECIMAL(15,2) | 부서 예산 |
| head_count | INT | 부서 인원수 |
| created_at | TIMESTAMP | 레코드 생성 시간 |

## Table: projects

프로젝트 정보를 관리하는 테이블입니다.

| Column | Type | Description |
|--------|------|-------------|
| project_id | INT PRIMARY KEY | 프로젝트 고유 ID |
| project_name | VARCHAR(200) | 프로젝트명 |
| description | TEXT | 프로젝트 설명 |
| start_date | DATE | 시작일 |
| end_date | DATE | 종료일 |
| status | ENUM('planning','active','completed','cancelled') | 프로젝트 상태 |
| budget | DECIMAL(15,2) | 프로젝트 예산 |
| department_id | INT | 담당 부서 ID (FK) |
| project_manager_id | INT | 프로젝트 매니저 ID (FK) |
| created_at | TIMESTAMP | 레코드 생성 시간 |
| updated_at | TIMESTAMP | 레코드 수정 시간 |

## Table: project_assignments

직원과 프로젝트 간의 할당 관계를 관리하는 테이블입니다.

| Column | Type | Description |
|--------|------|-------------|
| assignment_id | INT PRIMARY KEY | 할당 고유 ID |
| project_id | INT | 프로젝트 ID (FK) |
| employee_id | INT | 직원 ID (FK) |
| role | VARCHAR(100) | 프로젝트 내 역할 |
| assigned_date | DATE | 할당일 |
| completion_date | DATE | 완료일 |
| hours_allocated | INT | 할당된 시간 |
| status | ENUM('assigned','in_progress','completed') | 할당 상태 |

## Table: customers

고객 정보를 관리하는 테이블입니다.

| Column | Type | Description |
|--------|------|-------------|
| customer_id | INT PRIMARY KEY | 고객 고유 ID |
| company_name | VARCHAR(200) | 회사명 |
| contact_name | VARCHAR(100) | 담당자명 |
| contact_email | VARCHAR(100) | 담당자 이메일 |
| contact_phone | VARCHAR(20) | 담당자 전화번호 |
| address | VARCHAR(500) | 주소 |
| city | VARCHAR(100) | 도시 |
| country | VARCHAR(100) | 국가 |
| credit_limit | DECIMAL(15,2) | 신용 한도 |
| account_manager_id | INT | 담당 직원 ID (FK) |
| created_at | TIMESTAMP | 레코드 생성 시간 |
| updated_at | TIMESTAMP | 레코드 수정 시간 |

## Table: orders

주문 정보를 관리하는 테이블입니다.

| Column | Type | Description |
|--------|------|-------------|
| order_id | INT PRIMARY KEY | 주문 고유 ID |
| customer_id | INT | 고객 ID (FK) |
| order_date | DATE | 주문일 |
| required_date | DATE | 요청 배송일 |
| shipped_date | DATE | 실제 배송일 |
| status | ENUM('pending','processing','shipped','delivered','cancelled') | 주문 상태 |
| total_amount | DECIMAL(15,2) | 총 금액 |
| payment_method | VARCHAR(50) | 결제 방법 |
| shipping_address | VARCHAR(500) | 배송 주소 |
| notes | TEXT | 주문 메모 |
| created_by | INT | 주문 생성 직원 ID (FK) |
| created_at | TIMESTAMP | 레코드 생성 시간 |
| updated_at | TIMESTAMP | 레코드 수정 시간 |

## 관계 설명

- `employees.department_id` → `departments.department_id`: 직원이 속한 부서
- `employees.manager_id` → `employees.employee_id`: 직원의 관리자 (자기 참조)
- `projects.department_id` → `departments.department_id`: 프로젝트 담당 부서
- `projects.project_manager_id` → `employees.employee_id`: 프로젝트 매니저
- `project_assignments.project_id` → `projects.project_id`: 할당된 프로젝트
- `project_assignments.employee_id` → `employees.employee_id`: 할당된 직원
- `customers.account_manager_id` → `employees.employee_id`: 고객 담당 직원
- `orders.customer_id` → `customers.customer_id`: 주문한 고객
- `orders.created_by` → `employees.employee_id`: 주문 생성 직원