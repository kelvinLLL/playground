import argparse
import sys
import json

try:
    from duckduckgo_search import DDGS
except ImportError:
    print("Error: duckduckgo_search not installed.")
    sys.exit(1)

def search(query, max_results):
    # Synchronous search (DDGS().text is sync by default in recent versions, or handles async internally)
    # Note: duckduckgo_search API changes often. Using the most common pattern.
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        
    if not results:
        print(f"No results found for '{query}'.")
        return

    print(f"**Search Results for:** {query}\n")
    for i, res in enumerate(results, 1):
        print(f"{i}. **{res.get('title', 'Untitled')}**")
        print(f"   URL: {res.get('href', '')}")
        print(f"   {res.get('body', '')}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--max_results", type=int, default=5)
    args = parser.parse_args()
    
    try:
        search(args.query, args.max_results)
    except Exception as e:
        print(f"Error during search: {e}")
        sys.exit(1)
