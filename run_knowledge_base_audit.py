#!/usr/bin/env python3
"""
Simple script to run EIDBI Knowledge Base Audit

This script provides an easy way to run the comprehensive audit system
and generate reports for ongoing knowledge base monitoring.
"""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from knowledge_base_audit_system import KnowledgeBaseAuditor

async def run_audit():
    """Run a comprehensive knowledge base audit"""
    print("🚀 Starting EIDBI Knowledge Base Audit")
    print("=" * 50)
    
    # Initialize auditor
    auditor = KnowledgeBaseAuditor()
    
    try:
        # Perform comprehensive audit
        print("\n📊 Performing Comprehensive Audit...")
        audit_results = await auditor.perform_comprehensive_audit()
        
        # Display results
        print(f"\n✅ Audit Complete!")
        print(f"   • Total Topics: {audit_results['total_topics']}")
        print(f"   • Fully Covered: {audit_results['fully_covered']}")
        print(f"   • Partially Covered: {audit_results['partially_covered']}")
        print(f"   • Not Covered: {audit_results['not_covered']}")
        print(f"   • Duration: {audit_results['duration_seconds']:.1f} seconds")
        
        # Show priority topics
        print(f"\n🎯 Top Priority Topics:")
        for i, topic in enumerate(audit_results['priority_topics'][:5], 1):
            status_emoji = "✅" if topic['status'] == "Fully covered" else "⚠️"
            print(f"   {i}. {status_emoji} {topic['topic']}")
            print(f"      Coverage: {topic['coverage_score']:.1%} | Priority: {topic['priority_score']:.1f}/10.0")
        
        # Show files generated
        print(f"\n📁 Files Generated:")
        print(f"   • Coverage Matrix: {audit_results['coverage_matrix_file']}")
        print(f"   • Gap Analysis: {audit_results['gap_analysis_file']}")
        
        return audit_results
        
    except Exception as e:
        print(f"❌ Error during audit: {e}")
        return None

async def run_quick_audit():
    """Run a quick audit without content sourcing"""
    print("⚡ Running Quick Audit (Analysis Only)")
    print("-" * 40)
    
    auditor = KnowledgeBaseAuditor()
    
    try:
        # Just run the audit analysis
        current_coverage = await auditor._analyze_current_knowledge_base()
        coverage_matrix = await auditor._assess_topic_coverage(current_coverage)
        
        print(f"\n📊 Quick Results:")
        print(f"   • Total Chunks Analyzed: {current_coverage['total_chunks']}")
        print(f"   • Unique Sources: {current_coverage['unique_sources']}")
        
        # Show coverage summary
        fully_covered = sum(1 for c in coverage_matrix.values() if c.status.value == "Fully covered")
        partially_covered = sum(1 for c in coverage_matrix.values() if c.status.value == "Partially covered")
        not_covered = sum(1 for c in coverage_matrix.values() if c.status.value == "Not covered")
        
        print(f"   • Fully Covered: {fully_covered}")
        print(f"   • Partially Covered: {partially_covered}")
        print(f"   • Not Covered: {not_covered}")
        
        # Show lowest scoring topics
        sorted_topics = sorted(coverage_matrix.values(), key=lambda x: x.coverage_score)
        print(f"\n⚠️ Topics Needing Attention:")
        for topic in sorted_topics[:3]:
            print(f"   • {topic.topic}: {topic.coverage_score:.1%} coverage")
        
        return coverage_matrix
        
    except Exception as e:
        print(f"❌ Error during quick audit: {e}")
        return None

def main():
    """Main function with menu options"""
    print("🎯 EIDBI Knowledge Base Audit Tool")
    print("=" * 40)
    print("1. Full Comprehensive Audit")
    print("2. Quick Coverage Analysis")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == "1":
                print("\n🔍 Running Full Comprehensive Audit...")
                result = asyncio.run(run_audit())
                if result:
                    print(f"\n✅ Audit completed successfully!")
                    print(f"📁 Check the 'data/audit/' directory for detailed reports.")
                break
                
            elif choice == "2":
                print("\n⚡ Running Quick Coverage Analysis...")
                result = asyncio.run(run_quick_audit())
                if result:
                    print(f"\n✅ Quick audit completed!")
                break
                
            elif choice == "3":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Audit cancelled by user.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    main() 