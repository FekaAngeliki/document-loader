from pathlib import Path

# Test different patterns
test_paths = [
    "file.md",                    # Root level file
    "subfolder/file.md",         # Nested file
    "deep/nested/file.md"        # Deeply nested
]

patterns = ["*", "**/*", "**", "*/*"]

for path_str in test_paths:
    path = Path(path_str)
    print(f"\nPath: {path_str}")
    for pattern in patterns:
        result = path.match(pattern)
        print(f"  Pattern '{pattern}': {result}")