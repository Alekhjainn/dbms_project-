# Test Report

| Test Case | Input / Condition | Expected Result | Actual Result | Status |
|-----------|-------------------|-----------------|---------------|--------|
| `test_duplicate_isbn` | Insert Edition with existing ISBN | IntegrityError raised | IntegrityError raised | Pass |
| `test_duplicate_accession` | Insert Copy with existing Accession No | IntegrityError raised | IntegrityError raised | Pass |
| `test_second_active_issue_same_copy` | Insert Issue for copy already issued | IntegrityError raised (Unique Index) | IntegrityError raised | Pass |
| `test_return_before_issue_date` | Update Return Date < Issue Date | IntegrityError raised (CHECK) | IntegrityError raised | Pass |
| `test_negative_fine` | Insert Fine with amount = -5 | IntegrityError raised (CHECK) | IntegrityError raised | Pass |
| `test_borrowing_limit` | Issue 3rd book to Student (max 2) | DatabaseError raised (Trigger) | DatabaseError raised | Pass |
| `test_fine_calculation` | Return book 3 days late | Fine created with correct amt | Fine created correctly | Pass |
| `test_reservation_queue_ordering_compaction` | Cancel queue pos 2 | Queue pos 3 becomes 2 | Pos updated to 2 | Pass |
| `test_transaction_rollback` | Fail constraint inside transaction | Entire transaction aborted | Transaction rolled back | Pass |

*Run `python run.py --test` to verify.*
