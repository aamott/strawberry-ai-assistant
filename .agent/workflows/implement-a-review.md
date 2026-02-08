---
auto_execution_mode: 1
description: Implement review findings, suggestions, and plans
---

Reviews are like TODO lists. Check an item off when you've fixed it or implemented it. Delete the file if it's all checked off. Periodically, delete checked off items from the file. Reviews are stored in `./docs/reviews`. 

1. Choose reviewed items to fix or implement. If an item will impact other items, consider fixing it first. Otherwise, go through the simplest items first.
2. Run tests as you make changes. If they fail or throw warnings, go back and fix the issue. Never ask permission to run tests or install the requirements, just do it. If a package is missing, note it so the package can be added to the requirements then install it. 
3. Run ruff check periodically to ensure code quality. 
4. Once a review is complete, delete checked off items from the file, or delete the file if it's all checked off. 

For large, difficult problems, write a detailed plan. Include sequence diagrams, call charts, and text descriptions. Keep actual code minimal in the plan, but example snippets are fine. 