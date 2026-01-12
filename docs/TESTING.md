# Strawberry AI - Testing Documentation

## Running Tests

The primary workflow is to run Spoke tests using the `strawberry-test` runner.

## Spoke Tests (recommended)

Run from the `ai-pc-spoke` directory.

### 1) Run tests (minimal console output)

This runs `pytest` but keeps the terminal output compact and writes the full output to a log file.

```bash
strawberry-test
```

### Log file

By default, full pytest output is written to:

`ai-pc-spoke/.test-logs/latest.log` (overwritten each run)

Only the most recent `.test-logs/*.log` is kept by default (to reduce noise). To keep
additional logs, pass:

`strawberry-test --keep-other-logs`

### 2) Verbose output (full details in the terminal)

```bash
strawberry-test --show-all
```

You can also pass pytest verbosity and traceback style:

```bash
strawberry-test -v
strawberry-test --tb short
```

### 3) Compact output (print only the last N lines after the run)

```bash
strawberry-test --tail 120
```

### 4) Log reader (for LLM-friendly iteration in the terminal)

If a test run fails, use these commands to explore the failures without re-running tests:

```bash
strawberry-test --failures
strawberry-test --show-failure 1
strawberry-test --show-failure 2
```

Hide warnings summary sections while reading failures:

```bash
strawberry-test --failures --hide-warnings
strawberry-test --show-failure 1 --hide-warnings
```

To read the last lines from the latest log without running tests:

```bash
strawberry-test --tail-log 200
```

Hide warnings while tailing:

```bash
strawberry-test --tail-log 200 --hide-warnings
```

Search within the latest log (no re-run):

```bash
strawberry-test --grep "AssertionError" --after 40
strawberry-test --grep "FAILURES" --fixed-strings
```

Focus on a single failing test by searching for its name/nodeid (no re-run):

```bash
strawberry-test --test test_my_feature
strawberry-test --test test_my_feature --hide-warnings
```

### Custom log location

```bash
strawberry-test --log-file .test-logs/ci.log
```

## Hub Tests

Run from the `ai-hub` directory:

```bash
pytest tests/
```
