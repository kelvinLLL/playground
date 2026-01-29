# Skill: DuckDuckGo Search
Description: Search the web using DuckDuckGo (privacy-focused).

## When to use
Use this when you need to find real-time information, news, or answers from the web.
Preferred over 'web_search' for simple queries or when 'web_search' is unavailable.

## Usage
Run the script using `run_local_script` with the path relative to local skills directory:

`script_name="duckduckgo/duckduckgo.py"`
`args=["--query", "search term"]`

Example:
```python
run_local_script(script_name="duckduckgo/duckduckgo.py", args=["--query", "current weather"])
```
