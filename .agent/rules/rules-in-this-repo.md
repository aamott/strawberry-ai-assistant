---
trigger: always_on
---

# Hints for the Strawberry AI repo

Follow these rules and hints during dev. They'll help you maintain a consistent design. 

1. SUMMARY.md is the authoritative overview of this app. If it's not in your chat history, review it afresh. NEVER edit it unless explicitely told to. 
2. Testing: use strawberry-test (from the venv) as follows: 
```bash
strawberry-test                 # Run Spoke tests with compact terminal output; full output saved to .test-logs/latest.log
strawberry-test --help          # Show available options and how arguments are forwarded
strawberry-test --show-all      # Run tests and stream full pytest output to the terminal
strawberry-test --tail 120      # Run tests, then print only the last 120 lines of the run output
strawberry-test --failures      # List failures parsed from the latest log (no re-run required)
strawberry-test --show-failure 1 # Show details for failure #1 from the latest log (no re-run required)
strawberry-test --tail-log 200  # Print the last 200 lines from the latest log without running tests
```

If you need more information for testing, use docs/TESTING.md