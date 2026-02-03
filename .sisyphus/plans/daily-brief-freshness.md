# Plan: Optimize Daily Brief Freshness

## Objective
Ensure the Daily Brief worker strictly filters for recent (24h) news, preventing outdated information from appearing in the final report.

## Work Items

- [ ] 1. **Update `DailyBriefWorker` System Prompt**
    - Add strict guideline: "STRICTLY prioritize news from the last 24 hours."
    - Add instruction: "Ignore outdated information."

- [ ] 2. **Update `_phase_editorial` Prompt**
    - Reinforce the date constraint in the final synthesis prompt.
    - "Based on the following search results from today ({date})..." -> "Filter out any results older than {date}..."

## Verification
- Review code changes.
