---
name: block-long-retries
enabled: true
event: bash
pattern: (sleep\s+[0-9]+|&&\s*sleep|while\s+true|for\s+i\s+in|retry.*[0-9]+|until.*do)
action: block
---

🚫 **Long-Running Retry Blocked**

This pattern suggests a retry loop or sleep that may not be the best approach:

**Problems with retry loops:**
- Can hide underlying issues instead of fixing them
- May wait longer than necessary
- Can create resource contention
- Often indicate a need for different approach

**Better alternatives:**
1. **Use exponential backoff** if retry is truly needed
2. **Check for completion** instead of sleeping:
   ```bash
   # Instead of: sleep 60 && check_status
   # Use: while ! check_status; do sleep 5; done
   ```
3. **Investigate root cause** - why is the operation failing?
4. **Use webhook/polling** for async operations instead of polling

**If you need to proceed:**
- Set a maximum retry count
- Add timeout handling
- Log each retry attempt
- Consider idempotency of the operation

Would you like to proceed with this operation anyway? If so, please confirm.