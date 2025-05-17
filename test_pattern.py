from pathlib import Path

# Test path matching
relative_path = "azure-openai-assistants-functions.md"
path = Path(relative_path)

patterns = ['*', '**/*']

for pattern in patterns:
    result = path.match(pattern)
    print(f"Path: {relative_path}, Pattern: {pattern}, Match: {result}")

# Test with nested path
nested_path = "subfolder/test.md"
path2 = Path(nested_path)

for pattern in patterns:
    result = path2.match(pattern)
    print(f"Path: {nested_path}, Pattern: {pattern}, Match: {result}")