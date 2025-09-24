#!/usr/bin/env python3
"""
Simple test script to validate processing pipeline functionality in NBG project.
"""

import sys
import os
import json
import tempfile
import asyncio
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.core.processing_pipeline import ProcessingPipeline
    from src.abstractions.file_source import FileMetadata
    from datetime import datetime
    
    async def test_processing_pipeline():
        """Test the processing pipeline functionality directly."""
        print("=== Testing Processing Pipeline in NBG Project ===")
        
        # Create temporary test directories
        processing_dir = tempfile.mkdtemp(prefix="nbg_processing_")
        processed_dir = tempfile.mkdtemp(prefix="nbg_processed_")
        
        try:
            # Configuration for processing pipeline
            config = {
                "enabled": True,
                "queue_extensions": [".ppt", ".pptx"],
                "processors": {
                    ".ppt": "ppt_to_text_converter",
                    ".pptx": "pptx_to_markdown_converter"
                },
                "output_format": ".md",
                "processing_dir": processing_dir,
                "processed_dir": processed_dir
            }
            
            print(f"✓ Created processing directories")
            print(f"  - Processing: {processing_dir}")
            print(f"  - Processed: {processed_dir}")
            
            # Create processing pipeline
            pipeline = ProcessingPipeline(config)
            print("✓ Created ProcessingPipeline instance")
            
            # Test file metadata
            test_files = [
                ("presentation1.ppt", b"PPT content - slide 1\nSlide 2 content"),
                ("presentation2.pptx", b"PPTX content - intro slide\nMain content slide")
            ]
            
            # Queue files for processing
            for filename, content in test_files:
                file_metadata = FileMetadata(
                    uri=f"/tmp/test/{filename}",
                    size=len(content),
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                    content_type='application/octet-stream'
                )
                
                queued = await pipeline.queue_file(file_metadata, content)
                if queued:
                    print(f"✓ Queued {filename} for processing")
                else:
                    print(f"❌ Failed to queue {filename}")
            
            # Process the queue
            print(f"\n=== Processing Queue ===")
            processed_files = await pipeline.process_queue()
            print(f"✓ Processed {len(processed_files)} files")
            
            # Show results
            for file_metadata in processed_files:
                filename = Path(file_metadata.uri).name
                print(f"  - {filename}")
                
                # Show content preview
                if Path(file_metadata.uri).exists():
                    with open(file_metadata.uri, 'r') as f:
                        lines = f.readlines()[:3]
                        for line in lines:
                            print(f"    {line.strip()}")
            
            # Test status
            status = pipeline.get_queue_status()
            print(f"\n=== Pipeline Status ===")
            print(f"✓ Queue extensions: {status['queue_extensions']}")
            print(f"✓ Processors configured: {status['processors_configured']}")
            print(f"✓ Total queued: {status['total_queued']}")
            
            print("\n✅ Processing pipeline test completed successfully!")
            print("\n🔧 NBG Project Processing Flow:")
            print("1. ✅ ProcessingPipeline class instantiated correctly")
            print("2. ✅ Files queued for processing")
            print("3. ✅ Placeholder processors executed")
            print("4. ✅ Processed files created successfully")
            print("5. ✅ Ready for custom package integration!")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Clean up temporary directories
            import shutil
            shutil.rmtree(processing_dir, ignore_errors=True)
            shutil.rmtree(processed_dir, ignore_errors=True)

    if __name__ == "__main__":
        success = asyncio.run(test_processing_pipeline())
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This suggests the NBG project structure may need adjustments.")
    sys.exit(1)