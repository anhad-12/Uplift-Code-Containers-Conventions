# Handle missing users safely

Generated from isolated scenario copies using Bob modes. Original Bob predictions are preserved.

Base: {'passed': 52, 'failed': 0, 'errors': 0, 'skipped': 0, 'exitCode': 0}

Before repairs: {'passed': 46, 'failed': 6, 'errors': 0, 'skipped': 0, 'exitCode': 1}

After repairs: {'passed': 52, 'failed': 0, 'errors': 0, 'skipped': 0, 'exitCode': 0}

Repairs:
- shop/admin/reports.py
- shop/orders/invoice.py
- shop/orders/service.py
- shop/payments/charge.py
- shop/payments/receipt.py
- shop/users/routes.py

Verified: all collected tests pass; no collection errors. See the raw base/before/after JSON, XML and console logs for counts and commands.
