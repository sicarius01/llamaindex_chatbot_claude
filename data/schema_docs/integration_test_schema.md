---
database: integration_test_db
version: 2.0
author: Test Suite
---

# Integration Test Database Schema

## employees

Employee information management table.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| employee_id | INT NOT NULL | PK | Employee unique identifier |
| first_name | VARCHAR(50) NOT NULL | | Employee first name |
| last_name | VARCHAR(50) NOT NULL | | Employee last name |
| email | VARCHAR(100) NOT NULL | UNIQUE | Employee email address |
| phone | VARCHAR(20) | | Contact phone number |
| hire_date | DATE NOT NULL | | Date of hire |
| job_title | VARCHAR(100) | | Current job title |
| salary | DECIMAL(10,2) | | Annual salary |
| department_id | INT | FK | Department reference |
| manager_id | INT | FK | Manager's employee_id |

FK: department_id -> departments.department_id
FK: manager_id -> employees.employee_id

## departments

Department organizational structure.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| department_id | INT NOT NULL | PK | Department identifier |
| department_name | VARCHAR(100) NOT NULL | | Department name |
| location | VARCHAR(100) | | Office location |
| budget | DECIMAL(15,2) | | Annual budget |
| head_count | INT | | Number of employees |

## products

Product catalog table.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| product_id | INT NOT NULL | PK | Product identifier |
| product_name | VARCHAR(200) NOT NULL | | Product name |
| category | VARCHAR(50) | | Product category |
| price | DECIMAL(10,2) NOT NULL | | Unit price |
| stock_quantity | INT | | Current stock level |
| supplier_id | INT | FK | Supplier reference |

FK: supplier_id -> suppliers.supplier_id

## orders

Customer order tracking.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| order_id | INT NOT NULL | PK | Order identifier |
| customer_id | INT NOT NULL | FK | Customer reference |
| order_date | TIMESTAMP NOT NULL | | Order timestamp |
| total_amount | DECIMAL(12,2) | | Total order value |
| status | VARCHAR(20) | | Order status |
| shipping_address | TEXT | | Delivery address |

FK: customer_id -> customers.customer_id

## customers

Customer information.

| Column | Type | Key | Description |
|--------|------|-----|-------------|
| customer_id | INT NOT NULL | PK | Customer identifier |
| company_name | VARCHAR(100) | | Company name |
| contact_name | VARCHAR(100) NOT NULL | | Primary contact |
| email | VARCHAR(100) NOT NULL | | Contact email |
| phone | VARCHAR(20) | | Contact phone |
| credit_limit | DECIMAL(10,2) | | Maximum credit |
