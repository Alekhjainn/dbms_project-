# Business Rules & Implementation

This document maps business rules to the exact constraints or triggers enforcing them.

1. **One active issue per copy:**
   - *Implementation:* `CREATE UNIQUE INDEX idx_issue_active_copy ON Issue(copy_id) WHERE return_date IS NULL;`

2. **Valid dates (return cannot be before issue, due cannot be before issue):**
   - *Implementation:* Table-level `CHECK(due_date >= issue_date)` and `CHECK(return_date IS NULL OR return_date >= issue_date)`.

3. **Non-negative fines:**
   - *Implementation:* Table-level `CHECK(amount >= 0)` on `Fine`.

4. **Reservation queue ordering:**
   - *Implementation:* `CREATE UNIQUE INDEX idx_reservation_queue ON Reservation(edition_id, queue_position) WHERE status = 'Waiting';` and trigger `trg_reservation_compact` to re-compact positions.

5. **Member borrowing limit based on policy:**
   - *Implementation:* `trg_issue_check_member` trigger verifies active issues against `Loan_Policy.max_books`.

6. **Block issue if copy not available:**
   - *Implementation:* `trg_issue_check_available` trigger checks `Copy.status`.

7. **Block issue if member suspended or unpaid fines > 100:**
   - *Implementation:* `trg_issue_check_member` trigger aggregates unpaid fines.

8. **Automatic fine calculation on late return:**
   - *Implementation:* `trg_return_update_copy_and_fine` trigger checks `return_date > due_date` and calculates fine via `Loan_Policy.fine_per_day`.

9. **Automatic Copy Status Updates:**
   - *Implementation:* `trg_issue_update_copy` changes status to `Issued`. `trg_return_update_copy_and_fine` changes status to `Available` or `Reserved` if a queue exists.
