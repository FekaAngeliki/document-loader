import asyncio
from pathlib import Path
from src.implementations.file_system_source import FileSystemSource

async def debug_scan():
    config = {
        'root_path': '/Users/giorgosmarinos/Documents/scrapper-output',
        'include_patterns': ['**/*']
    }
    
    source = FileSystemSource(config)
    await source.initialize()
    
    print(f"Root path: {source.root_path}")
    print(f"Include patterns: {source.include_patterns}")
    print(f"Exclude patterns: {source.exclude_patterns}")
    
    # Try direct globbing
    print("\nDirect rglob results:")
    search_path = source.root_path
    count = 0
    for file_path in search_path.rglob('*'):
        if file_path.is_file():
            count += 1
            relative_path = file_path.relative_to(source.root_path)
            print(f"  File found: {relative_path}")
            result = source._should_include(str(relative_path))
            print(f"    Should include: {result}")
            
            # Debug pattern matching
            path = Path(str(relative_path))
            for pattern in source.include_patterns:
                match_result = path.match(pattern)
                print(f"    Pattern '{pattern}' match: {match_result}")
            
            if count > 5:  # Limit output
                print("  ... (more files)")
                break
    
    print(f"\nTotal files found with rglob: {count}")
    
    # Test list_files
    print("\nTesting list_files method:")
    files = await source.list_files()
    print(f"Files returned by list_files: {len(files)}")
    
    await source.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_scan())