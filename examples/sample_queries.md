# Sample Queries for Data Librarian

This document contains example questions you can ask Data Librarian along with expected behavior.

## General Discovery Questions

### "Where can I find customer data?"
**Expected Behavior:** Returns tables and columns related to customers, users, or client information. Should identify tables with names like `customers`, `users`, `clients`, etc.

### "What tables contain sales information?"
**Expected Behavior:** Returns tables related to sales, transactions, orders, or revenue. May include tables like `sales`, `orders`, `transactions`, `revenue`, etc.

### "Show me data about user activity"
**Expected Behavior:** Returns tables/columns tracking user actions, events, sessions, clicks, or engagement metrics.

### "Where is product information stored?"
**Expected Behavior:** Returns tables related to products, items, inventory, or catalog data.

## Specific Column Searches

### "Which columns contain email addresses?"
**Expected Behavior:** Returns columns with names like `email`, `email_address`, `user_email`, etc., along with their parent tables.

### "Find timestamp columns"
**Expected Behavior:** Returns columns with data types related to timestamps, dates, or datetime fields.

### "Where can I find user IDs?"
**Expected Behavior:** Returns columns named `user_id`, `customer_id`, `uid`, etc.

## Schema-Specific Questions

### "What's in the sales schema?"
**Expected Behavior:** Lists all tables in any schema named "sales" across all catalogs.

### "Show me tables in the production catalog"
**Expected Behavior:** Lists all schemas and tables within the "production" catalog.

## Data Relationship Questions

### "How do I join users and orders?"
**Expected Behavior:** Identifies tables containing user and order data, highlighting key columns that might be used for joins (e.g., `user_id`, `customer_id`).

### "What tables reference customer_id?"
**Expected Behavior:** Returns all tables and columns that contain `customer_id` or similar customer identifier columns.

## Data Type Specific

### "Find all JSON columns"
**Expected Behavior:** Returns columns with JSON or STRUCT data types.

### "Which tables have array columns?"
**Expected Behavior:** Returns tables containing array or list type columns.

## Example CLI Usage

```bash
# Basic question
data-librarian ask "Where can I find customer data?"

# With catalog filter
data-librarian ask "What sales data is available?" --catalog production

# With schema filter
data-librarian ask "Show me user tables" --catalog main --schema users

# Explore a specific schema
data-librarian explore production.sales

# Check system status
data-librarian status
```

## Example API Usage

```bash
# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Where can I find customer data?"}'

# Browse catalog
curl http://localhost:8000/catalog

# Get status
curl http://localhost:8000/status

# Trigger ingestion
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}'
```

## Tips for Effective Questions

1. **Be specific** - More specific questions yield better results
2. **Use domain terms** - Reference your actual data domains (customers, orders, products, etc.)
3. **Ask about relationships** - Data Librarian understands questions about how tables relate
4. **Filter when needed** - Use catalog/schema filters to narrow down results
5. **Iterate** - Refine your questions based on initial results
