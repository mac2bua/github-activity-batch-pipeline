---
name: warn-destructive-sql
enabled: true
event: bash
pattern: (TRUNCATE\s+(TABLE\s+)?|DROP\s+(TABLE|DATABASE|SCHEMA)\s+|DELETE\s+FROM\s+)
action: warn
---

⚠️ **Destructive SQL Command Detected**

You're about to run a destructive SQL command that can permanently delete data:
- `TRUNCATE TABLE` - Removes all rows from a table
- `DROP TABLE/DATABASE/SCHEMA` - Removes the entire object
- `DELETE FROM` - Removes rows (may be filtered)

**Before proceeding:**
1. Verify the target table/database is correct
2. Ensure you have a backup if needed
3. Consider using `WHERE` clause with `DELETE` to limit scope
4. For testing, consider creating a backup first

**Tip:** Use `CREATE TABLE backup AS SELECT * FROM table` before destructive operations.