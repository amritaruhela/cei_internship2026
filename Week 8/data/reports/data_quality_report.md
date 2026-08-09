# OmniMarket Data Quality & Audit Report

| Dataset | Initial Rows | Invalid Rows | Corrected | Rejected / Removed | Clean Rows | Issue Type | Resolution Strategy |
|---|---|---|---|---|---|---|---|
| Customers | 650 | 38 | 641 | 38 | 612 | Duplicate Keys & Syntax Invalid Emails | Trimmed, title-cased, imputed missing regions; rejected invalid emails and duplicate keys. |
| Products | 550 | 22 | 542 | 22 | 528 | Duplicate Keys & Invalid Prices/Costs | Trimmed, imputed subcategories; rejected zero/negative price records and duplicate keys. |
| Orders | 1500 | 126 | 1500 | 124 | 1376 | Orphan Foreign Keys, Malformed Dates, Invalid Statuses | Standardized status strings; rejected orphan orders, malformed/future dates, and invalid status codes. |
| Order Lines | 3200 | 429 | 3188 | 421 | 2779 | Zero/Negative Quantity, Excessive Discount, Missing Product/Order FK | Computed line_total_usd; rejected non-positive quantities, out-of-range discounts, and orphan line items. |
| Returns | 550 | 130 | 550 | 130 | 420 | Pre-order Return Timestamp, Quantity Overflow, Orphan Return FK | Standardized reason codes; rejected pre-order return dates, excessive return quantities, and unmapped returns. |