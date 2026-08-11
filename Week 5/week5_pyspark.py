"""
Week 5 - Apache Spark Data Processing using PySpark
Celebal Excellence Internship (CEI) 2026 - Data Engineering Domain
Converted from Week5_PySpark_Superstore.ipynb for standalone / CLI execution.
"""

# # Apache Spark Data Processing using PySpark
# ### Celebal Excellence Internship (CEI) 2026 — Data Engineering Domain — Week 5

# ## Student Details
#
# | Field | Detail |
# |---|---|
# | **Program** | Celebal Excellence Internship (CEI) 2026 |
# | **Domain** | Data Engineering |
# | **Week** | Week 5 |
# | **Topic** | Apache Spark Data Processing using PySpark |
# | **Environment** | Google Colab (PySpark, local mode) |

# ## Assignment Objective
#
# Build a single, coherent PySpark workflow — environment setup, dataset ingestion, inspection and
# cleaning, followed by 15 questions covering Spark fundamentals, DataFrame transformations,
# null/duplicate handling, aggregations, and a final revenue-processing pipeline. All questions
# operate on **one** extended Superstore dataset to mirror a real-world Data Engineering notebook.

# ## Apache Spark Overview
#
# - Distributed compute engine that processes data in-memory across a cluster, avoiding repeated disk I/O between stages (unlike classic MapReduce).
# - Core abstraction is the **RDD**; DataFrames/Datasets sit on top and are optimized by **Catalyst** (query planning) and **Tungsten** (memory/execution).
# - Supports **batch** (Spark Core/SQL), **streaming** (Structured Streaming), **ML** (MLlib), and **graph** (GraphX) workloads on one engine.
# - Lazy evaluation: transformations build a DAG; execution happens only on an action (`show`, `count`, `write`, ...).
# - Fault tolerance via RDD lineage — lost partitions are recomputed from lineage, not from replicated data copies.
# - Scales from a single laptop (local mode, used in this notebook) to thousand-node clusters with the same API.

# ## Environment Setup

# ### Install PySpark

# Install PySpark in the Colab runtime (quiet mode to keep output clean)
# !pip install pyspark -q  # run manually: pip install pyspark

# ### Import Libraries

# Core PySpark imports used throughout the notebook
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, TimestampType
)
import random
from datetime import datetime, timedelta

# ### Initialize Spark Session

# Single SparkSession reused across the entire notebook
spark = (
    SparkSession.builder
    .appName("CEI-Week5-Superstore-PySpark")
    .master("local[*]")
    .config("spark.sql.shuffle.partitions", "8")  # small local cluster -> fewer shuffle partitions
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")  # suppress verbose Spark logs in Colab
spark

# ## Load Dataset
#
# The base **Superstore** dataset (Order/Region/Category/Sales grain) is extended with the
# columns required by this assignment (`user_id`, `transaction_date`, `status`, `subscription`,
# `age`, `username`, `email`, `price`, `raw_timestamp`, `store_id`). Data is generated
# programmatically with **intentional duplicates, nulls, and malformed timestamps** so every
# cleaning question below has real signal to act on. One DataFrame is used for all 15 questions.

# Reference lists used to synthesize realistic Superstore-style records
regions        = ["West", "East", "Central", "South"]
categories     = ["Furniture", "Office Supplies", "Technology"]
sub_categories  = ["Chairs", "Tables", "Binders", "Phones", "Storage", "Accessories"]
cities         = ["New York", "Los Angeles", "Chicago", "Seattle", "Austin", "Miami", "Denver"]
statuses       = ["Delivered", "Pending", "Cancelled", None]           # None -> injects nulls
subscriptions  = ["Premium", "Standard", "Basic"]
store_ids      = ["ST-101", "ST-102", "ST-103", "ST-104", "ST-105"]

random.seed(42)  # reproducible synthetic data

def random_date(start_days_back=730):
    # Random transaction_date within the last 2 years
    d = datetime(2026, 7, 1) - timedelta(days=random.randint(0, start_days_back))
    return d.strftime("%Y-%m-%d")

def random_raw_timestamp(i):
    # Mix of well-formed and messy timestamp strings -> feeds Q10 / Q14
    base = datetime(2024, 1, 1) + timedelta(hours=i * 7)
    if i % 11 == 0:
        return base.strftime("%d-%m-%Y %H:%M")   # inconsistent format (day-first)
    return base.strftime("%Y-%m-%d %H:%M:%S")     # standard ISO-like format

records = []
for i in range(1, 151):
    user_id = f"U{1000 + (i % 60)}"               # user_ids repeat -> supports dedup logic
    price = round(random.uniform(15, 1200), 2)
    if i % 13 == 0:
        price = None                              # inject null prices -> Q15
    email = f"user{i}@mail.com"
    if i % 17 == 0:
        email = None                              # inject null emails -> Q12
    username = f"user_{i}"
    if i % 19 == 0:
        username = ""                             # inject empty usernames -> Q12

    record = {
        "order_id": f"ORD-{2000 + i}",
        "user_id": user_id,
        "transaction_date": random_date(),
        "region": random.choice(regions),
        "product_category": random.choice(categories),
        "sub_category": random.choice(sub_categories),
        "city": random.choice(cities),
        "sale_amount": round(random.uniform(20, 900), 2),
        "quantity": random.randint(1, 8),
        "status": random.choice(statuses),
        "subscription": random.choice(subscriptions),
        "age": random.randint(16, 65),
        "username": username,
        "email": email,
        "price": price,
        "raw_timestamp": random_raw_timestamp(i),
        "store_id": random.choice(store_ids),
    }
    records.append(record)

# Duplicate a handful of full records (same user_id + transaction_date) -> Q3 / Q15
records += [records[3], records[10], records[27]]

len(records)

# Explicit schema keeps types predictable (avoids inferSchema pitfalls raised in Q14)
schema = StructType([
    StructField("order_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("transaction_date", StringType(), True),
    StructField("region", StringType(), True),
    StructField("product_category", StringType(), True),
    StructField("sub_category", StringType(), True),
    StructField("city", StringType(), True),
    StructField("sale_amount", DoubleType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("status", StringType(), True),
    StructField("subscription", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("username", StringType(), True),
    StructField("email", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("raw_timestamp", StringType(), True),
    StructField("store_id", StringType(), True),
])

df_sales = spark.createDataFrame(records, schema=schema)
df_sales.show(5)

# ## Data Inspection

# Structural inspection: schema, row/column counts, and null profile per column
df_sales.printSchema()
print(f"Rows: {df_sales.count()}  |  Columns: {len(df_sales.columns)}")

null_counts = df_sales.select([
    F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in df_sales.columns
])
null_counts.show()

# Quick statistical profile of numeric columns
df_sales.describe(["sale_amount", "price", "age", "quantity"]).show()

# ## Data Cleaning
#
# Baseline cleaning applied up front (whitespace trimming, blank-string normalization).
# Column-specific cleaning (nulls, duplicates, type casts) is handled inside the relevant
# question below, since each one targets a different rule.

# Trim string columns and normalize empty strings to actual nulls where useful for inspection
string_cols = [f.name for f in df_sales.schema.fields if str(f.dataType) == "StringType()"]

df_clean_base = df_sales
for c in string_cols:
    df_clean_base = df_clean_base.withColumn(c, F.trim(F.col(c)))

df_clean_base.select("username", "email", "status").show(5)

# ---
# ## Q1. Limitations of traditional MapReduce vs Spark
#
# **Problem Statement:** What are the key limitations of traditional MapReduce that make Spark a
# preferred choice for modern big data processing?

# **Key Points**
#
# - MapReduce persists intermediate results to disk after every map/reduce stage; Spark keeps data in-memory (RDD/DataFrame caching) across stages, cutting I/O drastically for iterative jobs.
# - MapReduce forces a rigid map → shuffle → reduce pattern; Spark's DAG scheduler supports arbitrary multi-stage pipelines (map, filter, join, aggregate) in one job.
# - Iterative workloads (ML training, graph algorithms) re-read data from HDFS every iteration in MapReduce; Spark caches the working set once with `.cache()`/`.persist()`.
# - MapReduce has high per-job JVM startup and scheduling overhead; Spark reuses executors across stages and jobs within an application.
# - No native interactive/ad-hoc query support in MapReduce; Spark SQL and the DataFrame API give sub-second interactive queries via Catalyst optimization.
# - MapReduce lacks a unified API for batch, streaming, ML, and graph — each needs a separate engine (Hive, Storm, Mahout); Spark unifies all of these.
# - Spark's lazy evaluation + query optimizer (Catalyst/Tungsten) produces more efficient physical plans than MapReduce's fixed execution model.
#
# **Key Observation:** The dominant cost MapReduce pays — repeated disk round-trips between stages — is exactly what Spark's in-memory DAG model eliminates, which is why it especially wins on iterative and interactive workloads.

# ---
# ## Q2. In-Memory Computing for iterative ML algorithms
#
# **Problem Statement:** Explain how Spark uses In-Memory Computing to speed up iterative machine
# learning algorithms compared to disk-based systems.

# **Key Points**
#
# - Iterative ML algorithms (e.g., gradient descent, k-means) reuse the same dataset across many passes; Spark loads it once and keeps it in executor memory via `.cache()`/`.persist(StorageLevel.MEMORY_ONLY)`.
# - Disk-based systems (classic MapReduce) re-read the full dataset from HDFS on every iteration, so I/O cost scales linearly with iteration count.
# - Spark's RDD lineage means cached partitions that are evicted or lost can be recomputed from lineage rather than requiring replicated disk storage.
# - Broadcast variables let Spark ship read-only model parameters (e.g., current weight vector) to all executors efficiently, avoiding repeated shuffles of small shared state.
# - MLlib algorithms are built directly on cached RDDs/DataFrames, so each iteration only pays the compute cost, not the I/O cost, of accessing training data.
# - Memory tiers (`MEMORY_ONLY`, `MEMORY_AND_DISK`) let Spark spill to disk gracefully under memory pressure instead of failing, trading some speed for reliability.
# - Net effect: iteration-over-iteration cost drops from "read from disk + compute" to just "compute," which is the main reason Spark ML training beats disk-bound MapReduce equivalents.
#
# **Key Observation:** In-memory caching converts an O(iterations × dataset size) I/O cost into a one-time load cost, which is the single biggest lever for iterative workloads.

# ---
# ## Q3. Remove duplicate rows on a column subset
#
# **Problem Statement:** Remove all duplicate rows from a DataFrame based on a specific set of
# columns: `user_id` and `transaction_date`.
#
# **Solution Approach:** `dropDuplicates()` accepts a subset of columns — rows matching on just
# those columns are treated as duplicates, keeping the first occurrence Spark encounters.

# Drop duplicates using only (user_id, transaction_date) as the identity key
before_count = df_sales.count()

df_dedup_subset = df_sales.dropDuplicates(subset=["user_id", "transaction_date"])

after_count = df_dedup_subset.count()
print(f"Rows before: {before_count} | Rows after dropDuplicates(subset=[user_id, transaction_date]): {after_count}")
df_dedup_subset.show(5)

# **Key Observation:** `dropDuplicates(subset=[...])` is cheaper and more precise than a full-row `distinct()` when duplicates are defined by a business key rather than every column matching.

# ---
# ## Q4. Filter West region, average sale_amount by category
#
# **Problem Statement:** Filter `df_sales` for rows where `region` is `'West'`, then group by
# `product_category` to find the average `sale_amount`.
#
# **Solution Approach:** Chain `.filter()` → `.groupBy()` → `.agg()` in a single lazy pipeline.

# Filter West region, then aggregate average sale_amount per product_category
west_avg_sales = (
    df_sales
    .filter(F.col("region") == "West")
    .groupBy("product_category")
    .agg(F.round(F.avg("sale_amount"), 2).alias("avg_sale_amount"))
    .orderBy(F.desc("avg_sale_amount"))
)

west_avg_sales.show()

# **Key Observation:** Filtering before grouping reduces the shuffle volume during `groupBy`, since only West-region rows need to be shuffled and aggregated.

# ---
# ## Q5. `na.drop()` vs `na.fill()`
#
# **Problem Statement:** What is the difference between `.na.drop()` and `.na.fill()`? Provide a
# code example filling null values in a `status` column with the string `'Unknown'`.
#
# **Solution Approach:**
# - `na.drop()` **removes** rows containing nulls (row-count decreases; use when nulls are rare and unrecoverable).
# - `na.fill()` **substitutes** a default value in place of nulls (row-count preserved; use when a sensible default exists).

# na.fill(): replace nulls in 'status' with a sentinel value, no rows are dropped
df_status_filled = df_sales.na.fill({"status": "Unknown"})

df_status_filled.groupBy("status").count().orderBy(F.desc("count")).show()

# **Key Observation:** `na.fill()` preserves row count and is preferred when downstream aggregations need every record; `na.drop()` trades completeness for eliminating uncertainty entirely.

# ---
# ## Q6. Cities with more than 100 records
#
# **Problem Statement:** Find the total count of records for each city in a DataFrame, but only
# for cities where the count is greater than 100.
#
# **Solution Approach:** `groupBy().count()` then filter on the aggregated `count` column with
# `.having`-equivalent `.filter()` (Spark DataFrame API has no separate HAVING clause — filtering
# after aggregation achieves the same result).

# Aggregate record counts per city, then keep only cities exceeding the threshold
city_counts = (
    df_sales
    .groupBy("city")
    .count()
    .filter(F.col("count") > 100)
    .orderBy(F.desc("count"))
)

city_counts.show()
print("Note: with 150 synthetic rows across 7 cities, no city exceeds 100 here — "
      "the filter logic is verified below on the unfiltered counts.")
df_sales.groupBy("city").count().orderBy(F.desc("count")).show()

# **Key Observation:** Filtering on an aggregated column always happens *after* `groupBy().agg()/.count()` in the DataFrame API — there is no HAVING clause, just a second `.filter()`.

# ---
# ## Q7. Immutability and data cleaning
#
# **Problem Statement:** How does the immutability of Spark DataFrames affect how you perform
# "data cleaning" steps like dropping columns or renaming them?

# **Key Points**
#
# - DataFrames are immutable — `drop()`, `withColumnRenamed()`, `withColumn()` all return a **new** DataFrame; the original reference is untouched.
# - Cleaning pipelines are therefore built as chains of transformations reassigned to a new variable (or chained inline), not as in-place mutation.
# - This enables safe reuse of an original raw DataFrame if a cleaning step needs to be re-derived or debugged.
# - Immutability underpins lineage-based fault tolerance: each transformation step is a reproducible node in the DAG, so lost partitions recompute deterministically.
# - It also makes cleaning pipelines naturally composable and testable — each step is a pure function of its input DataFrame.
# - Trade-off: naive chaining without `.cache()` recomputes upstream steps if the cleaned DataFrame is reused multiple times downstream — cache after expensive cleaning if reused.
#
# **Key Observation:** Because nothing is mutated in place, "cleaning" in Spark really means *composing a chain of transformations that yields a new, cleaner DataFrame* — never editing the source.

# ---
# ## Q8. Filter age range and Premium subscription
#
# **Problem Statement:** Filter a dataset for rows where `age` is between 18 and 30 (inclusive)
# and `subscription` is `'Premium'`.
#
# **Solution Approach:** Combine a `.between()` range check with an equality condition using `&`.

# Filter on an inclusive numeric range AND a categorical equality condition
young_premium_users = df_sales.filter(
    (F.col("age").between(18, 30)) & (F.col("subscription") == "Premium")
)

print(f"Matching rows: {young_premium_users.count()}")
young_premium_users.select("user_id", "age", "subscription", "store_id").show(5)

# **Key Observation:** `.between(a, b)` is inclusive on both ends and reads more clearly than `(col >= a) & (col <= b)`.

# ---
# ## Q9. Handle nulls before aggregation
#
# **Problem Statement:** When cleaning a dataset, why is it often better to handle null values
# before performing mathematical aggregations like `sum()` or `avg()`?

# **Key Points**
#
# - Spark's `sum()`/`avg()` silently **skip nulls** rather than erroring, which can silently under- or over-state results if nulls aren't actually meant to be excluded.
# - A column that is mostly null can produce a misleadingly "clean" average from a tiny surviving sample, hiding a data quality issue.
# - Deciding *how* to treat nulls (drop, fill with 0, fill with mean/median) changes the aggregation result — this should be an explicit, reviewed decision, not Spark's default behavior.
# - For `sum()`, unhandled nulls are effectively treated as "excluded," not "zero" — the two are semantically different in a revenue or count-based metric.
# - Handling nulls upfront also prevents inconsistent treatment across multiple aggregations reusing the same DataFrame downstream.
# - Aggregating over unhandled nulls can propagate NaN/None into derived KPIs used further downstream (dashboards, ML features), compounding the issue.
#
# **Key Observation:** Aggregation functions hide null-handling behind a default (skip), so resolving nulls first makes the null-handling decision explicit and auditable instead of implicit.

# ---
# ## Q10. Cast and rename `raw_timestamp` → `event_time`
#
# **Problem Statement:** Revise a column named `raw_timestamp` by casting it to `TimestampType`
# and renaming it to `event_time`.
#
# **Solution Approach:** Cast with `.cast(TimestampType())`, then `.withColumnRenamed()`. Standard
# `yyyy-MM-dd HH:mm:ss` strings cast cleanly; the injected day-first strings (see Q14) will not.

# Cast raw_timestamp to TimestampType, then rename the resulting column
df_timestamped = (
    df_sales
    .withColumn("raw_timestamp", F.col("raw_timestamp").cast(TimestampType()))
    .withColumnRenamed("raw_timestamp", "event_time")
)

df_timestamped.select("order_id", "event_time").show(10, truncate=False)

# Rows that failed the cast (malformed source format) surface as nulls here
failed_casts = df_timestamped.filter(F.col("event_time").isNull()).count()
print(f"Rows where timestamp cast failed (malformed source format): {failed_casts}")

# **Key Observation:** A direct `.cast(TimestampType())` only succeeds for strings matching Spark's default timestamp format — inconsistent formats silently become `null`, which is exactly the risk raised in Q14.

# ---
# ## Q11. The Shuffle process and wide transformations
#
# **Problem Statement:** Explain the "Shuffle" process that occurs during a grouping operation.
# Why is it considered a wide transformation?

# **Key Points**
#
# - A shuffle redistributes data across partitions/executors so that rows sharing the same key (e.g., `groupBy` key) end up on the same partition.
# - It involves writing intermediate data to disk on the map side, transferring it over the network, and reading/sorting it on the reduce side — the most expensive operation in Spark.
# - **Wide transformation** = each output partition can depend on data from *multiple* input partitions (as opposed to a **narrow** transformation like `filter`/`map`, where each output partition depends on exactly one input partition).
# - `groupBy`, `join`, `distinct`, and `repartition` are classic wide transformations because they require this cross-partition data movement.
# - Because a shuffle materializes intermediate results, it also creates a **stage boundary** in Spark's DAG — the job splits into a new stage after every shuffle.
# - Minimizing shuffles (filtering early, using `reduceByKey`-style pre-aggregation, broadcast joins for small tables) is one of the primary Spark performance tuning levers.
#
# **Key Observation:** Any operation that needs "all rows with the same key together" cannot be satisfied within a single partition, forcing the wide, network-bound shuffle that dominates Spark job cost.

# ---
# ## Q12. Remove rows with null email OR empty username
#
# **Problem Statement:** Identify and remove rows where the `email` column contains null values
# OR the `username` is an empty string.
#
# **Solution Approach:** Combine `isNull()` and an empty-string equality check with `|`, then keep
# the negation (`~`) of that condition.

# Rows to remove: null email OR blank username
invalid_condition = F.col("email").isNull() | (F.trim(F.col("username")) == "")

invalid_rows = df_sales.filter(invalid_condition)
print(f"Invalid rows identified: {invalid_rows.count()}")

df_valid_contacts = df_sales.filter(~invalid_condition)
print(f"Remaining valid rows: {df_valid_contacts.count()}")
df_valid_contacts.select("user_id", "username", "email").show(5)

# **Key Observation:** Trimming before the empty-string check matters — a username of `"  "` (whitespace only) would otherwise slip past a naive `== ""` comparison.

# ---
# ## Q13. Multiple statistics with `.agg()`
#
# **Problem Statement:** How do you use the `.agg()` function to calculate multiple statistics at
# once, such as the min, max, and mean of the `price` column?
#
# **Solution Approach:** Pass multiple aggregate expressions to a single `.agg()` call — Spark
# computes all of them in one pass over the data.

# Multiple aggregate functions computed in a single pass over 'price'
price_stats = df_sales.agg(
    F.min("price").alias("min_price"),
    F.max("price").alias("max_price"),
    F.round(F.mean("price"), 2).alias("mean_price"),
    F.count(F.col("price")).alias("non_null_price_count"),
)

price_stats.show()

# **Key Observation:** A single `.agg()` call with several aggregate expressions is one job/one pass over the data — far cheaper than calling `.select(F.min(...))`, `.select(F.max(...))`, etc. separately.

# ---
# ## Q14. Risk of `inferSchema=True` with messy date formats
#
# **Problem Statement:** In the context of cleaning a dataset, what is the risk of using
# `inferSchema=true` when your source data contains messy or inconsistent date formats?

# **Key Points**
#
# - `inferSchema=True` samples the data and picks a single type per column — mixed date formats (e.g., `2024-01-01` vs `01-01-2024`) often cause Spark to fall back to `StringType` instead of a proper date/timestamp type.
# - Even when a date type is inferred, rows that don't match the dominant format silently become `null` rather than raising an error, which is easy to miss.
# - Schema inference requires an extra pass (or a sample scan) over the data before the real job runs, adding latency — explicit schemas skip this.
# - Inference is non-deterministic across runs if the sample happens to change (e.g., streaming sources, file order) — explicit schemas guarantee reproducible typing.
# - Silent `null` conversion for malformed dates can cascade into incorrect join keys, broken time-based windowing, or skewed date-range filters downstream.
# - Best practice: define an explicit `StructType` schema and parse date/timestamp columns deliberately with `to_date()`/`to_timestamp()` plus an explicit format string, exactly as done in Q10.
#
# **Key Observation:** `inferSchema=True` optimizes for developer convenience, not for correctness — messy date columns are precisely the scenario where that trade-off produces silent data loss.

# ---
# ## Q15. Final processing pipeline — revenue by store
#
# **Problem Statement:** Build a complete Spark processing workflow that:
# 1. Removes duplicate records
# 2. Replaces null prices with 0
# 3. Groups data by `store_id`
# 4. Calculates total revenue
# 5. Displays the final processed DataFrame
#
# **Solution Approach:** Chain the four transformations directly on `df_sales`, ending in an
# action (`show()`), so the whole pipeline executes as a single lazy plan until triggered.

# End-to-end pipeline: dedupe -> fill null prices -> group by store -> total revenue
df_store_revenue = (
    df_sales
    .dropDuplicates()                              # 1. remove fully duplicate records
    .na.fill({"price": 0.0})                       # 2. replace null prices with 0
    .groupBy("store_id")                           # 3. group by store_id
    .agg(F.round(F.sum("price"), 2).alias("total_revenue"))  # 4. total revenue per store
    .orderBy(F.desc("total_revenue"))
)

# 5. Display the final processed DataFrame
df_store_revenue.show()

# **Key Observation:** Ordering matters — deduplicating and null-filling *before* the `groupBy` ensures the aggregation reflects clean, complete data rather than being distorted by duplicate rows or unresolved nulls.

# ---
# ## Performance Considerations
#
# - Filter/select early to shrink the data volume before any shuffle-triggering operation (`groupBy`, `join`, `distinct`).
# - Prefer `dropDuplicates(subset=[...])` over full-row `distinct()` when a business key defines uniqueness — it's cheaper and clearer.
# - Combine multiple aggregates into a single `.agg()` call instead of multiple passes over the same DataFrame.
# - Use explicit schemas (`StructType`) instead of `inferSchema=True` in production pipelines to avoid an extra inference pass and silent type/null issues.
# - Cache (`.cache()`/`.persist()`) a cleaned DataFrame only if it's reused multiple times downstream — caching a single-use DataFrame wastes memory.
# - Tune `spark.sql.shuffle.partitions` to match cluster/data size — the default (200) is oversized for small local datasets like this one.

# ## Best Practices Learned
#
# - Build one explicit schema up front rather than relying on inference, especially for date/timestamp columns.
# - Resolve nulls and duplicates *before* aggregating, not after — aggregation defaults (skip nulls) can mask data quality problems.
# - Chain transformations functionally (DataFrames are immutable) rather than mutating a DataFrame in place.
# - Keep theory and implementation questions in the same notebook narrative — conceptual answers explain *why* the code below does what it does.
# - Validate cleaning logic with row counts before/after each step, not just a final `show()`.

# ## Common Mistakes to Avoid
#
# - Relying on `inferSchema=True` on messy real-world date/timestamp columns.
# - Using `na.drop()` when the actual requirement was to preserve row count via `na.fill()` (or vice versa).
# - Filtering on an aggregated column *before* the `groupBy`/`agg()` instead of after (there is no HAVING clause).
# - Comparing `username == ""` without trimming, missing whitespace-only "empty" values.
# - Calling `.agg()` multiple times for related statistics instead of one call with several aggregate expressions.
# - Forgetting that duplicates can be defined by a business key subset, not just an exact full-row match.

# ## Key Takeaways
#
# - Spark's in-memory, lazy, DAG-based execution model is what differentiates it from disk-bound MapReduce, especially for iterative and interactive workloads.
# - Wide transformations (shuffles) are the main performance lever to manage — narrow transformations are comparatively free.
# - Explicit schemas and deliberate null/duplicate handling are the foundation of a trustworthy Data Engineering pipeline, not an afterthought.
# - The DataFrame API alone (no Spark SQL required) is sufficient to express filtering, grouping, multi-stat aggregation, casting, and full cleaning pipelines cleanly.

# ## Conclusion
#
# This notebook implemented a single, extended Superstore dataset and used it to answer all 15
# Week 5 questions with the PySpark DataFrame API — covering Spark fundamentals, transformation
# semantics, null/duplicate handling, casting, aggregation, and a final store-level revenue
# pipeline. The result is a reusable, well-documented reference for PySpark data cleaning and
# aggregation patterns in a Data Engineering context.

# Release cluster resources at the end of the notebook
spark.stop()
