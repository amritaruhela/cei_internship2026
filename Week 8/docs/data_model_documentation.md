# OmniMarket Intelligence System (OMIS) - Enterprise Data Model Specification

## 1. Executive Summary & Architecture Overview
The **OmniMarket Intelligence System (OMIS)** data model is architected as an **Enterprise Star/Snowflake Hybrid Relational Model** optimized for high-performance e-commerce marketplace analytics in SQLite. 

The schema separates master dimensional entities (`dim_customers`, `dim_products`) from transactional fact tables (`fact_orders`, `fact_order_lines`, `fact_returns`) to enforce strict 3rd Normal Form (3NF) relational integrity while accelerating analytical aggregation via indexed foreign keys.

```
                      +-------------------+
                      |   dim_customers   |
                      +-------------------+
                      | PK customer_id    |
                      +---------+---------+
                                | 1
                                |
                                | N
                      +---------v---------+
                      |    fact_orders    |
                      +-------------------+
                      | PK order_id       |
                      | FK customer_id    |
                      +----+---------+----+
                           | 1       | 1
                           |         |
                         N |       N |
+-------------------+      |         |      +-------------------+
|   dim_products    |<-----+         +----->|   fact_returns    |
+-------------------+      |                +-------------------+
| PK product_id     |      |                | PK return_id      |
+---------+---------+      |                | FK order_id       |
          | 1              |                | FK product_id     |
          |                |                +-------------------+
        N |              N |
+---------v----------------v--+
|      fact_order_lines       |
+-----------------------------+
| PK line_item_id             |
| FK order_id                 |
| FK product_id               |
+-----------------------------+
```

---

## 2. Entity Schema & Specification

### 2.1 `dim_customers` (Customer Master Dimension)
* **Description**: Contains customer demographic attributes, tier classification, geographic location, and acquisition channel history.
* **Granularity**: One record per unique registered customer.

| Column Name | Data Type | Key Type | Nullable | Constraints / Valid Values | Business Meaning |
|---|---|---|---|---|---|
| `customer_id` | TEXT | PRIMARY KEY | No | Pattern: `CUST-XXXXXX` | Unique customer identifier |
| `full_name` | TEXT | None | No | Standardized Title Case | Customer's first and last name |
| `email_address` | TEXT | UNIQUE | No | Valid email syntax | Customer's primary contact email |
| `registration_date` | TEXT | None | No | Format: `YYYY-MM-DD` | Date account was created |
| `account_tier` | TEXT | None | No | `Standard`, `Preferred`, `VIP`, `Enterprise` | Customer loyalty & spending classification |
| `geo_city` | TEXT | None | No | Title Case string | Customer's primary city |
| `geo_state` | TEXT | None | No | 2-letter US State Code | Customer's primary state/region |
| `signup_channel` | TEXT | None | No | `Organic Search`, `Direct Referral`, `Paid Search`, `Social Media`, `Affiliate Network` | Acquisition marketing source |
| `is_active` | INTEGER | None | No | `0` (Inactive) or `1` (Active) | Account activity status |

---

### 2.2 `dim_products` (Product Catalog Dimension)
* **Description**: Contains catalog metadata, hierarchical categorization (Category -> Subcategory), brand tier, and financial pricing metrics.
* **Granularity**: One record per unique stock keeping unit (SKU).

| Column Name | Data Type | Key Type | Nullable | Constraints / Valid Values | Business Meaning |
|---|---|---|---|---|---|
| `product_id` | TEXT | PRIMARY KEY | No | Pattern: `PROD-XXXXXX` | Unique product identifier |
| `product_name` | TEXT | None | No | Non-empty string | Commercial product title |
| `category_name` | TEXT | None | No | 5 Major Categories | Top-level product taxonomy |
| `subcategory_name` | TEXT | None | No | Non-empty string | Granular product sub-category |
| `brand_tier` | TEXT | None | No | Non-empty string | Manufacturer / Brand name |
| `unit_cost_usd` | REAL | None | No | `CHECK(unit_cost_usd > 0)` | Internal cost of goods sold (COGS) |
| `list_price_usd` | REAL | None | No | `CHECK(list_price_usd > 0)` | Standard manufacturer list price |

---

### 2.3 `fact_orders` (Order Transaction Fact)
* **Description**: Stores header-level transaction details for every order placed on the marketplace platform.
* **Granularity**: One record per order transaction.

| Column Name | Data Type | Key Type | Nullable | Constraints / Valid Values | Business Meaning |
|---|---|---|---|---|---|
| `order_id` | TEXT | PRIMARY KEY | No | Pattern: `ORD-XXXXXX` | Unique order transaction identifier |
| `customer_id` | TEXT | FOREIGN KEY | No | References `dim_customers(customer_id)` | FK linking to placing customer |
| `order_timestamp` | TEXT | None | No | Format: `YYYY-MM-DD HH:MM:SS` | Exact timestamp order was placed |
| `fulfillment_status`| TEXT | None | No | `Delivered`, `Shipped`, `Processing`, `Cancelled`, `Returned` | Current order lifecycle state |
| `payment_gateway` | TEXT | None | No | `Credit Card`, `PayPal`, `Apple Pay`, `BNPL`, `Direct Bank Transfer` | Payment processing method |
| `shipping_state` | TEXT | None | No | 2-letter US State Code | State where order was shipped |
| `fulfillment_center`| TEXT | None | No | Pattern: `FC-XXXX-XX` | Logistics warehouse fulfilling order |

---

### 2.4 `fact_order_lines` (Order Line Item Fact)
* **Description**: Granular line-item level breakdown of products purchased within each order.
* **Granularity**: One record per distinct product line per order.

| Column Name | Data Type | Key Type | Nullable | Constraints / Valid Values | Business Meaning |
|---|---|---|---|---|---|
| `line_item_id` | TEXT | PRIMARY KEY | No | Pattern: `LINE-XXXXXXX` | Unique line item identifier |
| `order_id` | TEXT | FOREIGN KEY | No | References `fact_orders(order_id)` | FK linking to header order |
| `product_id` | TEXT | FOREIGN KEY | No | References `dim_products(product_id)` | FK linking to purchased product |
| `order_qty` | INTEGER | None | No | `CHECK(order_qty > 0)` | Number of units purchased |
| `unit_price_usd` | REAL | None | No | `CHECK(unit_price_usd > 0)` | Unit selling price at purchase |
| `discount_rate` | REAL | None | No | `CHECK(discount_rate >= 0.0 AND <= 0.50)` | Promotional discount rate applied |
| `line_total_usd` | REAL | None | No | `CHECK(line_total_usd >= 0.0)` | Calculated Net USD: `qty * unit_price * (1 - discount)` |

---

### 2.5 `fact_returns` (Product Returns Fact)
* **Description**: Records product returns processed by customer service and logistics.
* **Granularity**: One record per return event.

| Column Name | Data Type | Key Type | Nullable | Constraints / Valid Values | Business Meaning |
|---|---|---|---|---|---|
| `return_id` | TEXT | PRIMARY KEY | No | Pattern: `RET-XXXXXX` | Unique return transaction identifier |
| `order_id` | TEXT | FOREIGN KEY | No | References `fact_orders(order_id)` | FK linking to original order |
| `product_id` | TEXT | FOREIGN KEY | No | References `dim_products(product_id)` | FK linking to returned product |
| `return_timestamp` | TEXT | None | No | Format: `YYYY-MM-DD HH:MM:SS` | Timestamp return was processed |
| `returned_qty` | INTEGER | None | No | `CHECK(returned_qty > 0)` | Number of physical units returned |
| `return_reason_code`| TEXT | None | No | `Defective Item`, `Wrong Size`, `Changed Mind`, `Buyer Remorse`, `Late Delivery` | Customer service reason code |

---

## 3. Relationship Cardinality & Constraints

1. **`dim_customers` (1) : (N) `fact_orders`**
   * A single customer can place 0, 1, or many orders over their lifecycle.
   * Enforced via Foreign Key `fact_orders.customer_id -> dim_customers.customer_id` (`ON DELETE CASCADE`).

2. **`fact_orders` (1) : (N) `fact_order_lines`**
   * An order must consist of 1 or many line items.
   * Enforced via Foreign Key `fact_order_lines.order_id -> fact_orders.order_id` (`ON DELETE CASCADE`).

3. **`dim_products` (1) : (N) `fact_order_lines`**
   * A product can be referenced across 0, 1, or many order line items.
   * Enforced via Foreign Key `fact_order_lines.product_id -> dim_products.product_id` (`ON DELETE RESTRICT`).

4. **`fact_orders` (1) : (N) `fact_returns`**
   * An order can have 0, 1, or many product returns.
   * Enforced via Foreign Key `fact_returns.order_id -> fact_orders.order_id` (`ON DELETE CASCADE`).

5. **`dim_products` (1) : (N) `fact_returns`**
   * A product can be returned across 0, 1, or many return records.
   * Enforced via Foreign Key `fact_returns.product_id -> dim_products.product_id` (`ON DELETE RESTRICT`).
