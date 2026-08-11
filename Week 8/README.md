# OmniMarket Customer & Order Intelligence System (OMIS)

![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite%203-lightgrey.svg)
![Pandas](https://img.shields.io/badge/Data-Pandas%203.0-orange.svg)
![Build Status](https://img.shields.io/badge/Pipeline-Passing-brightgreen.svg)
![Tests](https://img.shields.io/badge/Tests-12%2F12%20Passed-success.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

An enterprise-grade, independent **E-Commerce Marketplace Analytics & Customer Intelligence Platform** engineered in Python, SQL, and SQLite for the CEI Internship Final Mini-Project.

---

## 📄 Executive Summary & Business Context
**OmniMarket Intelligence System (OMIS)** analyzes multi-vendor e-commerce marketplace operations, customer purchasing dynamics, fulfillment efficiency, product returns, customer retention, revenue growth, customer segmentation, and cohort behavior.

Unlike generic order-processing projects, OMIS features a rich marketplace domain model comprising 5 relational entities (`customers`, `products`, `orders`, `order_lines`, `returns`), a non-destructive data cleaning engine with quarantine protocols, an advanced 20-query SQL analytics suite (featuring Window Functions, CTEs, and Self-Joins), a Customer Cohort Retention Matrix engine, an interactive CLI reporting application with Period-over-Period (PoP) comparison, high-resolution analytical visualizations, and automated unit testing for 12 edge cases.

---

## 🏗️ System Architecture

```
                                +---------------------------+
                                |      main.py (CLI / ETL)  |
                                +-------------+-------------+
                                              |
                +-----------------------------+-----------------------------+
                |                                                           |
    +-----------v-----------+                                   +-----------v-----------+
    |  Data Generation      |                                   |  Interactive CLI App  |
    |  (src/generation)     |                                   |  (src/reporting/cli)  |
    +-----------+-----------+                                   +-----------+-----------+
                |                                                           |
                v                                                           v
    +-----------+-----------+                                   +-----------+-----------+
    |  Cleaning & Governance|                                   | SQL Analytics Engine  |
    |  (src/cleaning)       |                                   | (src/analytics)       |
    +-----------+-----------+                                   +-----------+-----------+
                |                                                           |
                v                                                           v
    +-----------+-----------+                                   +-----------+-----------+
    |  SQLite Database      |                                   | Visualizer Engine     |
    |  (omnimarket.db)      |---------------------------------->| (src/reporting)       |
    +-----------------------+                                   +-----------------------+
```

---

## 📁 Repository Structure

```
d:\SHL\week 8\
├── data/
│   ├── raw/                  # Raw generated CSVs with intentional DQ anomalies
│   ├── cleaned/              # Cleaned & standardized CSV datasets
│   ├── rejected/             # Quarantined invalid records (rejection logs)
│   ├── reports/              # Formal Data Quality audit reports (CSV & MD)
│   └── omnimarket_analytics.db # SQLite normalized relational database
├── sql/
│   ├── schema.sql            # DDL: Tables, PRIMARY/FOREIGN keys, CHECK constraints, Indexes
│   ├── basic.sql             # Queries 1-3: Category revenue, Top customers, Monthly trends
│   ├── intermediate.sql      # Queries 4-8: Zero purchase accounts, Returns, AOV, Regional
│   └── advanced.sql          # Queries 1-12: Window functions, CTEs, Cohort, YoY, Self-joins
├── src/
│   ├── __init__.py
│   ├── config.py             # System constants, paths, seed = 42, threshold rules
│   ├── generation/
│   │   ├── __init__.py
│   │   └── generator.py      # Reproducible synthetic data generator (>500 records/entity)
│   ├── validation/
│   │   ├── __init__.py
│   │   └── validator.py      # Modular regex, date, range, FK validation rules
│   ├── cleaning/
│   │   ├── __init__.py
│   │   └── cleaner.py        # ETL cleaning, imputation, quarantine & DQ audit engine
│   ├── database/
│   │   ├── __init__.py
│   │   └── db_manager.py     # SQLite connection lifecycle & schema loader
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── analytics_engine.py # Python wrapper for SQL queries
│   │   └── cohort_analysis.py  # Cohort retention matrix & RFM segmentation
│   └── reporting/
│       ├── __init__.py
│       ├── cli.py            # Terminal interactive UI & PoP reporting app
│       └── visualizer.py     # Matplotlib analytical chart generator
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py      # Automated unittest suite covering 12 edge cases
├── docs/
│   ├── charts/               # Rendered PNG analytical charts (8 high-res charts)
│   ├── data_model_documentation.md # Detailed schema & ERD documentation
│   └── project_report.md     # Formal 22-section CEI internship report
├── main.py                   # Main CLI & ETL pipeline entrypoint
├── requirements.txt          # Python package dependencies
└── README.md                 # Project documentation
```

---

## 📊 Relational Data Model

The database is built on a **3NF Star/Snowflake Hybrid Relational Schema**:

* **`dim_customers`** (613 clean rows): Primary Key `customer_id`, Full Name, Unique Email, Registration Date, Tier (`Standard`, `Preferred`, `VIP`, `Enterprise`), City, State, Channel, Active Status.
* **`dim_products`** (528 clean rows): Primary Key `product_id`, Product Name, Category, Subcategory, Brand Tier, Unit Cost USD, List Price USD.
* **`fact_orders`** (1,377 clean rows): Primary Key `order_id`, FK `customer_id`, Timestamp, Fulfillment Status (`Delivered`, `Shipped`, `Processing`, `Cancelled`, `Returned`), Payment Gateway, Shipping State.
* **`fact_order_lines`** (2,781 clean rows): Primary Key `line_item_id`, FK `order_id`, FK `product_id`, Quantity, Unit Price USD, Discount Rate, Line Total USD.
* **`fact_returns`** (421 clean rows): Primary Key `return_id`, FK `order_id`, FK `product_id`, Return Timestamp, Returned Quantity, Reason Code.

---

## 🛠️ Data Quality & Cleaning Strategy

Raw data is injected with controlled, documented anomalies to rigorously test data governance:
* **Syntax Flaws**: Invalid emails (`user@@domain.com`, missing `@`), extra whitespace, mixed case names/cities.
* **Range Violations**: Zero/negative prices, negative order quantities, discounts > 50%.
* **Referential Integrity**: Orphan orders referencing non-existent customers, orphan line items.
* **Logical Anomalies**: Return timestamps preceding order timestamps, return quantity > purchased quantity.

**Governance Actions**:
* **Correct & Standardize**: Trim whitespace, Title Case names/cities, uppercase state codes.
* **Impute**: Replace missing non-critical attributes with defaults (`"Unknown"`, `"General Accessories"`).
* **Reject & Quarantine**: Isolate unfixable records into `data/rejected/rejected_<entity>.csv`.
* **Audit Report**: Generates `data/reports/data_quality_report.md` tracking initial rows, invalid count, corrected count, rejected count, and clean count.

---

## 🔍 SQL Analytics Suite

OMIS features 20 production SQL queries organized across 3 script files:

### Basic Analytics (`sql/basic.sql`)
1. **Revenue by Category**: Gross revenue, discount impact, net revenue by category.
2. **Top Customers by Lifetime Spend**: Top 15 accounts ranked by cumulative net spend.
3. **Monthly Order Trends**: Monthly order volume, active customer count, AOV.

### Intermediate Analytics (`sql/intermediate.sql`)
4. **Friction Analysis**: Customers with order history but zero completed purchases.
5. **High Return Products**: Products with high return quantities and return-to-sales ratios.
6. **Category Return Rates**: Return percentages and financial refund impact.
7. **AOV by Customer Tier**: Monetization across Standard, Preferred, VIP, Enterprise.
8. **Regional Revenue Contribution**: State revenue shares and market penetration.

### Advanced SQL (`sql/advanced.sql`)
1. **Running Regional Revenue**: `SUM() OVER (PARTITION BY shipping_state ORDER BY order_timestamp)`.
2. **Product Rank within Category**: `DENSE_RANK() OVER (PARTITION BY category_name ORDER BY net_revenue DESC)`.
3. **Inter-Purchase Days Elapsed**: `LAG(order_timestamp) OVER (PARTITION BY customer_id ORDER BY order_timestamp)`.
4. **Repeat Purchase Cadence**: Average days between orders grouped by account tier.
5. **Customer Churn Risk**: Inactivity identification (>90 days since last purchase).
6. **Monthly RFM Segmentation**: Recency, Frequency, Monetary scoring via CTEs.
7. **Spend Quartiles**: `NTILE(4) OVER (ORDER BY total_spend DESC)`.
8. **Month-over-Month Growth**: MoM dollar and percentage revenue growth (`LAG`).
9. **Customer Product Journey**: First vs Most Recent product purchased (`ROW_NUMBER`).
10. **Pareto 80/20 Contribution**: Cumulative customer spend vs total revenue (`SUM OVER`).
11. **Cohort Retention Analysis**: Signup month cohorts vs Month 0, 1, 2, 3+ retention.
12. **Product Co-Purchase Analysis**: Basket analysis via Self-Join on `fact_order_lines`.

---

## 💻 CLI Reporting Application

Run the interactive terminal app:

```bash
python main.py
```

### Options Available:
* `[1] Daily Intelligence Summary`
* `[2] Weekly Performance Report`
* `[3] Monthly Executive Report & MoM Analysis`
* `[4] Custom Date Range Report`
* `[5] Execute Full End-to-End Data Pipeline`
* `[6] Run SQL Analytics Suite`
* `[7] Generate Visualizations & Charts`
* `[8] Exit`

To run the pipeline non-interactively from scratch:

```bash
python main.py --pipeline
```

---

## 🧪 Automated Edge Case Testing

Execute the automated test suite using Python's standard library `unittest`:

```bash
python -m unittest discover tests
```

### Tested Edge Cases (12/12 Passing):
1. Invalid Foreign Key Rejection
2. Invalid Email Syntax Validation
3. Invalid Date Range & Parsing
4. Primary Key Deduplication
5. Zero Quantity Rejection
6. Negative Quantity Rejection
7. Out-of-Bounds Discount Rate
8. Empty Dataset Pipeline Execution
9. Customers with Zero Orders
10. Products with Zero Sales
11. Return Without Corresponding Purchase
12. Date Range Query with No Matching Records

---

## 📋 Requirement-to-Implementation Audit Matrix

| Official CEI Requirement | Project Implementation | Primary File | Execution Status |
|---|---|---|---|
| Synthetic Dataset Generation (>500 rows) | Synthesized 5 datasets (650 Cust, 550 Prod, 1500 Ord, 3200 Lines, 550 Ret) | `src/generation/generator.py` | Verified (Pass) |
| Controlled Data Quality Flaws | Injected syntax, range, duplicate, FK, and timestamp errors | `src/generation/generator.py` | Verified (Pass) |
| Data Governance & Quarantine | Modular cleaning, imputation, and quarantine to `data/rejected/` | `src/cleaning/cleaner.py` | Verified (Pass) |
| Data Quality Audit Report | Generates before/after audit metrics CSV and MD | `data/reports/data_quality_report.md` | Verified (Pass) |
| SQLite Database & DDL Schema | 3NF Star/Snowflake schema with PK, FK, CHECK, and Indexes | `sql/schema.sql`, `src/database/db_manager.py` | Verified (Pass) |
| Basic SQL Suite (Q1-Q3) | Category revenue, Top customers, Monthly trends | `sql/basic.sql` | Verified (Pass) |
| Intermediate SQL Suite (Q4-Q8) | Friction, Returns, Category return rate, AOV, Regional | `sql/intermediate.sql` | Verified (Pass) |
| Advanced SQL Suite (Q1-Q12) | Window functions, CTEs, Cohort, YoY, Basket Self-Joins | `sql/advanced.sql` | Verified (Pass) |
| Customer Cohort Retention | Signup month cohorts vs Month 0..3+ retention matrix | `src/analytics/cohort_analysis.py` | Verified (Pass) |
| Customer RFM Segmentation | VIP, High Value, Regular, Occasional, At Risk classification | `src/analytics/cohort_analysis.py` | Verified (Pass) |
| Interactive CLI BI Application | Dynamic terminal app with Period-over-Period (PoP) comparison | `src/reporting/cli.py`, `main.py` | Verified (Pass) |
| Visualizations Suite | 8 high-res analytical charts saved to `docs/charts/` | `src/reporting/visualizer.py` | Verified (Pass) |
| Automated Edge Case Testing | 12 unit tests using standard `unittest` framework | `tests/test_pipeline.py` | Verified (Pass) |
| Comprehensive Project Documentation | 22-section project report and schema specification | `docs/project_report.md`, `docs/data_model_documentation.md` | Verified (Pass) |

---

## 📈 Learning Outcomes & Skills Demonstrated
* **Software Engineering**: Modular architecture, configuration management, type hints, docstrings, clean error handling.
* **Data Engineering**: Data synthesis, regex syntax validation, data quality governance, quarantine patterns, ETL pipeline design.
* **Relational Database Design**: 3NF schema design, DDL constraints, foreign key cascades, index tuning in SQLite.
* **Advanced Analytical SQL**: Window functions (`SUM OVER`, `DENSE_RANK`, `LAG`, `NTILE`), nested CTEs, self-joins.
* **Business Intelligence & Analytics**: Customer cohort retention matrices, RFM customer segmentation, basket analysis, Period-over-Period (PoP) reporting.
* **Quality Assurance**: Unit testing, boundary validation, edge-case coverage.
