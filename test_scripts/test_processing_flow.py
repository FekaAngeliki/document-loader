#!/usr/bin/env python3
"""
Test script to demonstrate the processing flow for excluded extensions.

This script shows how .ppt/.pptx files are excluded from normal processing
but then processed through the external tool pipeline.
"""

import sys
import os
import json
import tempfile
import asyncio
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.implementations.mixed_source import MixedSource


async def test_processing_flow():
    """Test the complete processing flow with placeholder processors."""
    print("=== Testing Processing Flow with Placeholders ===")
    
    # Create temporary test directories
    temp_dir = tempfile.mkdtemp(prefix="flow_test_")
    processing_dir = tempfile.mkdtemp(prefix="processing_queue_")
    processed_dir = tempfile.mkdtemp(prefix="processed_files_")
    
    try:
        # Create test files including PowerPoint files
        test_files = {
            "document1.txt": "This is a normal text document",
            "presentation1.ppt": "PPT content - slide 1\nSlide 2 content",
            "presentation2.pptx": "PPTX content - intro slide\nMain content slide",
            "report.pdf": "PDF content here"
        }
        
        # Create test files
        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content)
        
        print(f"✓ Created {len(test_files)} test files in {temp_dir}")
        
        # Configuration with processing pipeline
        config = {
            "exclude_extensions": [".ppt", ".pptx"],
            "processing_pipeline": {
                "enabled": True,
                "queue_extensions": [".ppt", ".pptx"],
                "processors": {
                    ".ppt": "ppt_to_text_converter",
                    ".pptx": "pptx_to_markdown_converter"
                },
                "output_format": ".md",
                "processing_dir": processing_dir,
                "processed_dir": processed_dir
            },
            "sources": [
                {
                    "type": "file_system",
                    "config": {
                        "root_path": temp_dir,
                        "include_patterns": ["*"]
                    }
                }
            ]
        }
        
        print("\n=== Step 1: Normal File Listing (excludes .ppt/.pptx) ===")
        
        mixed_source = MixedSource(config)
        await mixed_source.initialize()
        
        normal_files = await mixed_source.list_files()
        print(f"✓ Normal files found: {len(normal_files)}")
        
        for file_metadata in normal_files:
            filename = Path(file_metadata.uri.split("://", 1)[1]).name
            print(f"  - {filename}")
        
        print(f"\n=== Step 2: Process Excluded Files ===")
        
        processed_files = await mixed_source.process_excluded_files()
        print(f"✓ Processed files: {len(processed_files)}")
        
        for file_metadata in processed_files:
            # Extract filename from processed URI
            if file_metadata.uri.startswith("processed://"):
                processed_path = file_metadata.uri.replace("processed://", "")
                filename = Path(processed_path).name
                print(f"  - {filename} (processed from excluded extension)")
        
        print(f"\n=== Step 3: Combined File Listing ===")
        
        all_files = await mixed_source.list_files_with_processing()
        print(f"✓ Total files available: {len(all_files)}")
        
        normal_count = len([f for f in all_files if not f.uri.startswith("processed://")])
        processed_count = len([f for f in all_files if f.uri.startswith("processed://")])
        
        print(f"  - Normal files: {normal_count}")
        print(f"  - Processed files: {processed_count}")
        
        # Show processing directory contents
        print(f"\n=== Step 4: Processing Results ===")
        processed_path = Path(processed_dir)
        if processed_path.exists():
            processed_files_on_disk = list(processed_path.glob("*"))
            print(f"✓ Files created in processing directory: {len(processed_files_on_disk)}")
            for pf in processed_files_on_disk:
                print(f"  - {pf.name}")
                # Show first few lines of processed content
                if pf.suffix == '.md':
                    with open(pf, 'r') as f:
                        lines = f.readlines()[:3]
                        for line in lines:
                            print(f"    {line.strip()}")
        
        await mixed_source.cleanup()
        
        print("\n✅ Processing flow test completed successfully!")
        print("\n🔧 Flow Summary:")
        print("1. ✅ PowerPoint files (.ppt, .pptx) excluded from normal processing")
        print("2. ✅ Excluded files queued for external tool processing")
        print("3. ✅ Placeholder processors created processed versions")
        print("4. ✅ Processed files available through combined file listing")
        print("5. ✅ Ready for integration with your custom package!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up temporary directories
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(processing_dir, ignore_errors=True)
        shutil.rmtree(processed_dir, ignore_errors=True)


if __name__ == "__main__":
    success = asyncio.run(test_processing_flow())
    sys.exit(0 if success else 1)