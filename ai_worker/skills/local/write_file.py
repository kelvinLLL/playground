import sys
import os

if len(sys.argv) < 3:
    print("Usage: write_file.py <path> <content>")
    sys.exit(1)

path = sys.argv[1]
# content might be split if spaces are present and not quoted properly by the caller,
# but usually subprocess passes args correctly.
# However, if content has newlines, it might be tricky in argv.
# Better to read content from stdin?
# Or assume the caller passes it as a single string argument.
content = sys.argv[2]

# Ensure directory
try:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    with open(path, "w") as f:
        f.write(content)

    print(f"File written to {path}")
except Exception as e:
    print(f"Error writing file: {e}")
    sys.exit(1)
