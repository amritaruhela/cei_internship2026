# Week 7 Assignment — Brief Summary

**Dataset:** Superstore (Kaggle) — 9,994 rows, 21 columns, retail order-level transactions.

## What was done
- Loaded the CSV into Pandas and validated the load with `head()`, `tail()`, `shape`, `info()`, `describe()`.
- Assessed data quality: **0 missing values** and **0 duplicate rows** in this extract. The identify/handle logic (median-fill for numeric columns, drop rows missing critical IDs) was implemented in full even though it wasn't triggered on this batch, so the notebook works unchanged on messier data.
- Cleaned column names to snake_case, converted `Order Date`/`Ship Date` to proper `datetime`, trimmed whitespace on text columns.
- Demonstrated filtering, column selection, sorting, and groupby aggregation.
- Engineered `unit_price` (Sales ÷ Quantity, since no raw Price column exists) and the required `total_amount = unit_price × quantity`, plus `profit_margin_pct` and `order_processing_days`.
- Ran EDA: sales by region/category/segment, top 10 products, profit by category, average order value.
- Produced 4 chart types (bar, line, box plot, correlation heatmap).
- Exported the cleaned dataset to `cleaned_superstore.csv` (9,994 rows, 26 columns).

## Key figures
- Total sales: **$2,297,200.86**
- Total profit: **$286,397.02**
- Average order value: **$458.61**
- Top region by sales: **West**
- Top category by sales: **Technology**

## Key business insight
Furniture generates strong revenue but disproportionately low profit compared to Technology and Office Supplies, and discount rate correlates negatively with profit margin — suggesting Furniture's discounting policy is eroding its margins.
