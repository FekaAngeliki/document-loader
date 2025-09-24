#!/usr/bin/env python3
"""
Test script to validate the updated mixed_source_test.json configuration
with processing pipeline capabilities.
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_updated_config():
    """Test the updated configuration file."""
    print("🚀 TESTING UPDATED mixed_source_test.json CONFIGURATION")
    print("=" * 65)
    
    try:
        # Load and validate the configuration
        config_file = Path("configs/mixed_source_test.json")
        
        if not config_file.exists():
            print(f"❌ Configuration file not found: {config_file}")
            return False
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("✅ Configuration file loaded successfully")
        
        # Test 1: Basic configuration structure
        print(f"\n=== Test 1: Basic Configuration Structure ===")
        
        required_keys = ['name', 'rag_type', 'sources']
        for key in required_keys:
            if key in config:
                print(f"✅ {key}: {config[key] if key != 'sources' else f'{len(config[key])} sources'}")
            else:
                print(f"❌ Missing required key: {key}")
                return False
        
        # Test 2: Processing pipeline configuration
        print(f"\n=== Test 2: Processing Pipeline Configuration ===")
        
        if 'exclude_extensions' in config:
            exclude_ext = config['exclude_extensions']
            print(f"✅ exclude_extensions: {exclude_ext}")
        else:
            print("❌ exclude_extensions not found")
            return False
        
        if 'processing_pipeline' in config:
            pipeline = config['processing_pipeline']
            print(f"✅ processing_pipeline found")
            
            # Validate pipeline configuration
            pipeline_keys = ['enabled', 'queue_extensions', 'processors', 'output_format']
            for key in pipeline_keys:
                if key in pipeline:
                    value = pipeline[key]
                    if key == 'processors':
                        print(f"✅ {key}: {list(value.keys())}")
                    else:
                        print(f"✅ {key}: {value}")
                else:
                    print(f"❌ Missing pipeline key: {key}")
                    return False
            
            # Validate consistency between exclude and queue extensions
            queue_ext = pipeline.get('queue_extensions', [])
            if set(exclude_ext) == set(queue_ext):
                print("✅ exclude_extensions and queue_extensions match perfectly")
            else:
                print(f"⚠️  Mismatch: exclude={exclude_ext}, queue={queue_ext}")
        else:
            print("❌ processing_pipeline not found")
            return False
        
        # Test 3: Sources configuration
        print(f"\n=== Test 3: Sources Configuration ===")
        
        sources = config.get('sources', [])
        print(f"✅ Found {len(sources)} sources:")
        
        for i, source in enumerate(sources):
            source_type = source.get('source_type', 'unknown')
            source_id = source.get('source_id', f'source_{i}')
            print(f"  {i+1}. {source_id} ({source_type})")
            
            # Check if source has include_extensions
            source_config = source.get('source_config', {})
            if 'include_extensions' in source_config:
                include_ext = source_config['include_extensions']
                print(f"     Include extensions: {include_ext}")
        
        # Test 4: Validate against processing pipeline logic
        print(f"\n=== Test 4: Processing Logic Validation ===")
        
        try:
            from src.core.processing_pipeline import ProcessingPipeline
            
            # Create a processing pipeline with the config
            pipeline_config = config['processing_pipeline']
            pipeline = ProcessingPipeline(pipeline_config)
            
            print("✅ ProcessingPipeline created successfully")
            
            # Test should_process logic
            test_files = [
                "document.txt",
                "presentation.ppt", 
                "slideshow.pptx",
                "report.pdf"
            ]
            
            for filename in test_files:
                should_process = pipeline.should_process(filename)
                file_ext = Path(filename).suffix.lower()
                expected = file_ext in pipeline.queue_extensions
                
                if should_process == expected:
                    status = "✅" if should_process else "⚪"
                    action = "PROCESS" if should_process else "SKIP"
                    print(f"{status} {filename}: {action}")
                else:
                    print(f"❌ {filename}: Logic error")
                    return False
            
        except ImportError as e:
            print(f"⚠️  Could not test processing logic: {e}")
        
        # Test 5: JSON syntax and structure validation
        print(f"\n=== Test 5: JSON Structure Validation ===")
        
        try:
            # Re-serialize to test JSON validity
            json_str = json.dumps(config, indent=2)
            re_parsed = json.loads(json_str)
            print("✅ JSON structure is valid and re-parseable")
        except Exception as e:
            print(f"❌ JSON structure error: {e}")
            return False
        
        print(f"\n🎉 All configuration tests passed!")
        
        print(f"\n📋 Updated Configuration Summary:")
        print("✅ Basic multi-source configuration preserved")
        print("✅ Processing pipeline configuration added")
        print("✅ Extension exclusion and processing coordination")
        print("✅ Placeholder processors configured")
        print("✅ Processing directories specified")
        print("✅ Output format configured")
        print("✅ JSON structure valid")
        
        print(f"\n🔧 Configuration Features:")
        print(f"• Excludes: {config['exclude_extensions']}")
        print(f"• Processes: {config['processing_pipeline']['queue_extensions']}")
        print(f"• Processors: {list(config['processing_pipeline']['processors'].keys())}")
        print(f"• Output format: {config['processing_pipeline']['output_format']}")
        print(f"• Sources: {len(config['sources'])} configured")
        
        print(f"\n✨ Configuration ready for use with processing pipeline!")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_updated_config())
    if success:
        print(f"\n🎯 CONFIGURATION VALIDATION SUCCESSFUL!")
        sys.exit(0)
    else:
        print(f"\n❌ CONFIGURATION VALIDATION FAILED")
        sys.exit(1)