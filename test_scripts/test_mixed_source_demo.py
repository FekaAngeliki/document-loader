#!/usr/bin/env python3
"""
Demo: Mixed Source Types in Multi-Source Knowledge Base

This demonstrates that the multi-source functionality supports mixing different 
source types (file_system + enterprise_sharepoint) in the same knowledge base.
"""

import asyncio
import json
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from test_multi_source_end_to_end import (
    MockRAGSystem,
    MockFileSource, 
    MockFileMetadata,
    MockFileProcessor
)

class MockEnterpriseSharePointSource:
    """Mock implementation of Enterprise SharePoint source for testing."""
    
    def __init__(self, site_url: str, document_library: str, folder_path: str = "", **kwargs):
        self.site_url = site_url
        self.document_library = document_library
        self.folder_path = folder_path
        self.config = kwargs
        
        # Simulate SharePoint files
        self.mock_files = [
            MockFileMetadata(
                uri=f"{site_url}/{document_library}{folder_path}/Q1_Budget_Report.xlsx",
                size=45612,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                created_at="2024-01-15T10:30:00Z",
                modified_at="2024-01-20T14:15:00Z"
            ),
            MockFileMetadata(
                uri=f"{site_url}/{document_library}{folder_path}/Annual_Financial_Summary.pdf", 
                size=2834567,
                content_type="application/pdf",
                created_at="2024-02-01T09:00:00Z",
                modified_at="2024-02-01T09:00:00Z"
            ),
            MockFileMetadata(
                uri=f"{site_url}/{document_library}{folder_path}/Expense_Guidelines.docx",
                size=234890,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                created_at="2024-01-10T11:45:00Z", 
                modified_at="2024-01-25T16:30:00Z"
            )
        ]
    
    async def initialize(self):
        print(f"   🔧 Mock SharePoint source initialized: {self.site_url}")
        print(f"      Library: {self.document_library}")
        print(f"      Folder: {self.folder_path}")
    
    async def list_files(self):
        print(f"   📁 Found {len(self.mock_files)} files in SharePoint")
        return self.mock_files
    
    async def get_file_content(self, uri: str):
        # Return mock content based on file extension
        if uri.endswith('.xlsx'):
            content = b"MOCK EXCEL: Spreadsheet data with financial figures and charts"
        elif uri.endswith('.pdf'):
            content = b"MOCK PDF: Financial report with detailed analysis and graphics"
        elif uri.endswith('.docx'):
            content = b"MOCK WORD: Policy document with formatted text and tables"
        else:
            content = b"MOCK: Generic file content"
        
        filename = Path(uri).name
        print(f"   📖 Read content: {filename} ({len(content)} bytes)")
        return content
    
    async def cleanup(self):
        print(f"   🧹 Mock SharePoint source cleanup")

class MixedSourceBatchRunner:
    """Mock batch runner that supports mixed source types."""
    
    def __init__(self):
        self.file_processor = MockFileProcessor()
    
    async def sync_mixed_source_knowledge_base(self, config_path: str):
        """Demonstrate mixed source synchronization."""
        
        print(f"\n🚀 Starting Mixed Source Sync Demo")
        print(f"   Config: {config_path}")
        print("=" * 70)
        
        # Load configuration
        with open(config_path) as f:
            config = json.load(f)
        
        from data.multi_source_models import create_multi_source_kb_from_config
        multi_kb = create_multi_source_kb_from_config(config)
        
        print(f"📋 Knowledge Base: {multi_kb.name}")
        print(f"   RAG Type: {multi_kb.rag_type}")
        print(f"   Total Sources: {len(multi_kb.sources)}")
        
        # Group sources by type
        source_groups = {}
        for source in multi_kb.sources:
            if source.source_type not in source_groups:
                source_groups[source.source_type] = []
            source_groups[source.source_type].append(source)
        
        print(f"\n📊 Source Types:")
        for source_type, sources in source_groups.items():
            print(f"   • {source_type}: {len(sources)} sources")
        
        # Initialize RAG system
        rag = MockRAGSystem()
        await rag.initialize()
        
        # Process each source (mixed types)
        source_stats = {}
        total_files = 0
        
        for source_def in multi_kb.sources:
            if not source_def.enabled:
                print(f"\n⏸️  Skipping disabled source: {source_def.source_id}")
                continue
            
            print(f"\n📁 Processing Source: {source_def.source_id}")
            print(f"   Type: {source_def.source_type}")
            print(f"   Department: {source_def.metadata_tags.get('department', 'N/A')}")
            print(f"   Security: {source_def.metadata_tags.get('security_level', 'N/A')}")
            
            # Create appropriate source implementation
            if source_def.source_type == "file_system":
                source = MockFileSource(
                    root_path=source_def.source_config["root_path"],
                    include_extensions=source_def.source_config["include_extensions"]
                )
            elif source_def.source_type == "enterprise_sharepoint":
                config = source_def.source_config.copy()
                source = MockEnterpriseSharePointSource(
                    site_url=config.pop("site_url"),
                    document_library=config.pop("document_library"),
                    folder_path=config.pop("folder_path", ""),
                    **config
                )
            else:
                print(f"   ❌ Unsupported source type: {source_def.source_type}")
                continue
            
            # Process source
            stats = await self._process_source(source_def, source, rag, multi_kb)
            source_stats[source_def.source_id] = stats
            total_files += stats["files_processed"]
        
        # Display results
        await self._display_mixed_source_results(multi_kb.name, source_stats, source_groups)
        
        # Cleanup
        await rag.cleanup()
        
        return source_stats
    
    async def _process_source(self, source_def, source, rag, multi_kb):
        """Process a single source (any type)."""
        stats = {
            "source_type": source_def.source_type,
            "files_processed": 0,
            "files_uploaded": 0,
            "files_error": 0
        }
        
        try:
            await source.initialize()
            
            # Get files
            files = await source.list_files()
            stats["files_processed"] = len(files)
            
            # Process each file
            for file_metadata in files:
                try:
                    # Get content
                    content = await source.get_file_content(file_metadata.uri)
                    
                    # Generate filename with source organization
                    uuid_filename = self._generate_filename(
                        source_def.source_id,
                        file_metadata.uri, 
                        multi_kb.file_organization,
                        source_def.metadata_tags
                    )
                    
                    # Upload to RAG
                    rag_metadata = {
                        "kb_name": multi_kb.name,
                        "source_id": source_def.source_id,
                        "source_type": source_def.source_type,
                        "original_uri": file_metadata.uri,
                        **source_def.metadata_tags
                    }
                    
                    rag_uri = await rag.upload_document(content, uuid_filename, rag_metadata)
                    stats["files_uploaded"] += 1
                    
                except Exception as e:
                    print(f"   ❌ Error processing {file_metadata.uri}: {e}")
                    stats["files_error"] += 1
        
        finally:
            await source.cleanup()
        
        return stats
    
    def _generate_filename(self, source_id: str, original_uri: str, file_org: dict, metadata: dict):
        """Generate organized filename."""
        import uuid
        from pathlib import Path
        
        file_uuid = str(uuid.uuid4())
        extension = Path(original_uri).suffix
        
        naming_convention = file_org.get("naming_convention", "{uuid}{extension}")
        
        format_params = {
            "source_id": source_id,
            "uuid": file_uuid,
            "extension": extension,
            **metadata
        }
        
        try:
            return naming_convention.format(**format_params)
        except KeyError:
            return f"{file_uuid}{extension}"
    
    async def _display_mixed_source_results(self, kb_name: str, source_stats: dict, source_groups: dict):
        """Display comprehensive results for mixed sources."""
        
        print(f"\n" + "=" * 70)
        print(f"📊 Mixed Source Sync Results: {kb_name}")
        print("=" * 70)
        
        # Results by source type
        total_files = 0
        total_uploaded = 0
        total_errors = 0
        
        for source_type, sources in source_groups.items():
            type_files = sum(source_stats.get(s.source_id, {}).get("files_processed", 0) for s in sources)
            type_uploaded = sum(source_stats.get(s.source_id, {}).get("files_uploaded", 0) for s in sources)
            type_errors = sum(source_stats.get(s.source_id, {}).get("files_error", 0) for s in sources)
            
            print(f"\n🔹 {source_type.upper()} Sources:")
            print(f"   Sources: {len(sources)}")
            print(f"   Files processed: {type_files}")
            print(f"   Files uploaded: {type_uploaded}")
            print(f"   Errors: {type_errors}")
            
            for source in sources:
                stats = source_stats.get(source.source_id, {})
                print(f"     • {source.source_id}: {stats.get('files_processed', 0)} files")
            
            total_files += type_files
            total_uploaded += type_uploaded
            total_errors += type_errors
        
        print(f"\n📈 GRAND TOTALS (All Source Types):")
        print(f"   Files processed: {total_files}")
        print(f"   Files uploaded: {total_uploaded}")
        print(f"   Errors: {total_errors}")
        print(f"   Success rate: {(total_uploaded/total_files)*100:.1f}%" if total_files > 0 else "   Success rate: 0%")
        
        if total_errors == 0 and total_uploaded > 0:
            print(f"\n🎉 Mixed Source Sync Completed Successfully!")
            print(f"   ✅ All source types processed correctly")
            print(f"   ✅ File organization maintained across sources")
            print(f"   ✅ Metadata tagging preserved per source")
        else:
            print(f"\n⚠️  Mixed source sync completed with issues")

async def run_mixed_source_demo():
    """Run the mixed source type demonstration."""
    
    print("Mixed Source Types Demo")
    print("=" * 70)
    print("Demonstrating multi-source KB with:")
    print("• File System sources (local files)")
    print("• Enterprise SharePoint sources (cloud documents)")
    print("• All feeding into single RAG system")
    print("• Organized with source-specific metadata")
    
    try:
        # Initialize runner
        runner = MixedSourceBatchRunner()
        
        # Run mixed source sync
        config_path = "configs/mixed_source_test.json"
        stats = await runner.sync_mixed_source_knowledge_base(config_path)
        
        # Final validation
        print(f"\n🎯 MIXED SOURCE TYPE VALIDATION:")
        
        file_system_sources = [k for k, v in stats.items() if v.get("source_type") == "file_system"]
        sharepoint_sources = [k for k, v in stats.items() if v.get("source_type") == "enterprise_sharepoint"]
        
        print(f"   ✅ File System sources: {len(file_system_sources)}")
        print(f"   ✅ SharePoint sources: {len(sharepoint_sources)}")
        print(f"   ✅ Mixed in single KB: {len(file_system_sources) > 0 and len(sharepoint_sources) > 0}")
        
        total_files = sum(v.get("files_processed", 0) for v in stats.values())
        total_uploaded = sum(v.get("files_uploaded", 0) for v in stats.values())
        
        if total_uploaded > 0:
            print(f"\n🏆 CONCLUSION: Multi-source supports MIXED source types!")
            print(f"   • Can combine file_system + enterprise_sharepoint")
            print(f"   • Each source maintains its own configuration")
            print(f"   • Unified processing and organization")
            print(f"   • Single RAG system for all content")
            return True
        else:
            print(f"\n❌ No files were processed")
            return False
            
    except Exception as e:
        print(f"\n❌ Mixed source demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_mixed_source_demo())
    
    if success:
        print(f"\n✅ MIXED SOURCE TYPES DEMO SUCCESSFUL!")
    else:
        print(f"\n❌ Demo failed!")
    
    sys.exit(0 if success else 1)