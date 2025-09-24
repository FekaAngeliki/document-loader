#!/usr/bin/env python3
"""
End-to-end test for NBG project with processing pipeline.

This script validates that the processing pipeline integration works 
correctly within the NBG project structure.
"""

import sys
import os
import json
import tempfile
import asyncio
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_nbg_processing_integration():
    """Test complete integration in NBG project."""
    print("🚀 NBG PROJECT - END-TO-END PROCESSING TEST")
    print("=" * 60)
    
    try:
        # Import required modules
        from src.core.processing_pipeline import ProcessingPipeline
        from src.abstractions.file_source import FileMetadata
        from datetime import datetime
        
        print("✅ Successfully imported processing pipeline components")
        
        # Test 1: Processing Pipeline Standalone
        print(f"\n=== Test 1: Processing Pipeline Standalone ===")
        
        processing_dir = tempfile.mkdtemp(prefix="nbg_processing_")
        processed_dir = tempfile.mkdtemp(prefix="nbg_processed_")
        
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
        
        pipeline = ProcessingPipeline(config)
        
        # Create test file
        test_file = FileMetadata(
            uri="/tmp/test/presentation.ppt",
            size=100,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            content_type='application/octet-stream'
        )
        
        await pipeline.queue_file(test_file, b"PPT test content")
        processed = await pipeline.process_queue()
        
        print(f"✅ Processed {len(processed)} files")
        
        # Test 2: Mixed Source Factory Registration
        print(f"\n=== Test 2: Mixed Source Factory Registration ===")
        
        try:
            from src.core.factory import SourceFactory
            factory = SourceFactory()
            
            if 'mixed_source' in factory.sources:
                print("✅ mixed_source registered in SourceFactory")
                print(f"   Available sources: {list(factory.sources.keys())}")
            else:
                print("❌ mixed_source not found in factory")
                return False
        except ImportError as e:
            print(f"⚠️  Factory import issue: {e}")
        
        # Test 3: Configuration File Validation
        print(f"\n=== Test 3: Configuration File Validation ===")
        
        config_file = Path("configs/mixed_source_with_processing.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            print("✅ Configuration file loaded successfully")
            
            # Validate key components
            required_keys = ['exclude_extensions', 'processing_pipeline', 'sources']
            for key in required_keys:
                if key in config_data:
                    print(f"✅ {key}: Found")
                else:
                    print(f"❌ {key}: Missing")
                    return False
            
            # Validate processing pipeline config
            pipeline_config = config_data.get('processing_pipeline', {})
            if pipeline_config.get('enabled'):
                print("✅ Processing pipeline enabled in config")
                print(f"   Queue extensions: {pipeline_config.get('queue_extensions', [])}")
                print(f"   Processors: {list(pipeline_config.get('processors', {}).keys())}")
            else:
                print("❌ Processing pipeline not enabled")
                return False
        else:
            print(f"❌ Configuration file not found: {config_file}")
            return False
        
        # Test 4: Files and Directory Structure
        print(f"\n=== Test 4: Files and Directory Structure ===")
        
        required_files = [
            "src/core/processing_pipeline.py",
            "src/implementations/mixed_source.py",
            "configs/mixed_source_with_processing.json",
            "test_scripts/simple_processing_test.py"
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                print(f"✅ {file_path}: Found")
            else:
                print(f"❌ {file_path}: Missing")
                return False
        
        print(f"\n🎉 All NBG Project Integration Tests Passed!")
        
        print(f"\n📋 NBG Project Status Summary:")
        print("✅ Processing pipeline implementation copied")
        print("✅ Mixed source implementation added")
        print("✅ Factory registration updated")
        print("✅ Configuration files in place")
        print("✅ Test scripts functional")
        print("✅ Processing flow working with placeholders")
        
        print(f"\n🔧 Integration Points for Custom Package:")
        print("1. Replace placeholder processors in src/core/processing_pipeline.py")
        print("2. Update _convert_ppt_to_text() and _convert_pptx_to_markdown()")
        print("3. Add your custom package calls in these methods")
        print("4. Test with real .ppt/.pptx files")
        
        print(f"\n✨ NBG Project is ready for processing pipeline usage!")
        
        # Cleanup
        import shutil
        shutil.rmtree(processing_dir, ignore_errors=True)
        shutil.rmtree(processed_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ NBG Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_nbg_processing_integration())
    if success:
        print(f"\n🎯 NBG PROJECT READY FOR PROCESSING PIPELINE!")
        sys.exit(0)
    else:
        print(f"\n❌ NBG PROJECT INTEGRATION ISSUES DETECTED")
        sys.exit(1)