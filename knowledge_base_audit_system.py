#!/usr/bin/env python3
"""
EIDBI Knowledge Base Audit and Enhancement System

This system performs comprehensive audits of the EIDBI knowledge base,
identifies gaps, sources missing content, and continuously improves coverage.

Author: AI Assistant
Date: January 26, 2025
"""

import json
import csv
import logging
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import re
import time
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('knowledge_base_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CoverageStatus(Enum):
    """Coverage status for knowledge base topics"""
    FULLY_COVERED = "Fully covered"
    PARTIALLY_COVERED = "Partially covered"
    NOT_COVERED = "Not covered"

class TopicCategory(Enum):
    """Categories of EIDBI knowledge topics"""
    BILLING_CLAIMS = "Billing and Claims Procedures"
    PROVIDER_NETWORK = "Provider Network and Availability"
    SERVICE_DESCRIPTIONS = "Service Descriptions and Scope"
    ELIGIBILITY_ENROLLMENT = "Eligibility and Enrollment Processes"
    POLICIES_COMPLIANCE = "Program Policies and Compliance"
    TRAINING_SUPPORT = "Training and Support Resources"
    FUNDING_BUDGET = "Funding and Budget Information"
    OUTCOMES_QUALITY = "Outcome Measures and Quality Assurance"
    TECHNOLOGY_TOOLS = "Technology and Tools"

@dataclass
class TopicCoverage:
    """Data structure for topic coverage analysis"""
    topic: str
    category: TopicCategory
    status: CoverageStatus
    coverage_score: float  # 0.0 to 1.0
    document_count: int
    chunk_count: int
    key_documents: List[str]
    missing_subtopics: List[str]
    last_updated: datetime
    priority_score: float  # 1-10, higher = more important
    notes: str

@dataclass
class DataSource:
    """Data source for content collection"""
    name: str
    url: str
    source_type: str
    priority: int
    last_accessed: Optional[datetime] = None
    success_rate: float = 0.0
    content_quality: float = 0.0

@dataclass
class ContentItem:
    """Individual content item from data sources"""
    id: str
    title: str
    content: str
    source: str
    url: str
    category: TopicCategory
    extracted_date: datetime
    confidence_score: float
    metadata: Dict[str, Any]

class KnowledgeBaseAuditor:
    """Main class for knowledge base auditing and enhancement"""
    
    def __init__(self, data_dir: str = "data/audit"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize topic definitions
        self.topic_definitions = self._initialize_topic_definitions()
        
        # Initialize data sources
        self.data_sources = self._initialize_data_sources()
        
        # Coverage matrix
        self.coverage_matrix: Dict[str, TopicCoverage] = {}
        
        # Audit history
        self.audit_history: List[Dict[str, Any]] = []
        
        logger.info("Knowledge Base Auditor initialized")

    def _initialize_topic_definitions(self) -> Dict[TopicCategory, Dict[str, Any]]:
        """Initialize comprehensive topic definitions with keywords and subtopics"""
        return {
            TopicCategory.BILLING_CLAIMS: {
                "keywords": [
                    "billing", "claims", "reimbursement", "payment", "invoice", 
                    "medicaid", "medical assistance", "MA", "fee schedule", 
                    "prior authorization", "claim submission", "denial", "appeal"
                ],
                "subtopics": [
                    "EIDBI billing codes", "Prior authorization process", 
                    "Claim submission procedures", "Reimbursement rates",
                    "Billing documentation requirements", "Appeal processes",
                    "Medicaid billing guidelines", "Fee schedules"
                ],
                "required_documents": [
                    "Provider billing manual", "Fee schedule", "Prior auth forms",
                    "Claim submission guidelines", "Appeal procedures"
                ]
            },
            TopicCategory.PROVIDER_NETWORK: {
                "keywords": [
                    "provider", "network", "directory", "availability", "capacity",
                    "qualified supervising professional", "QSP", "BCBA", "therapist",
                    "enrollment", "credentialing", "geographic distribution"
                ],
                "subtopics": [
                    "Provider enrollment process", "Credentialing requirements",
                    "Geographic distribution", "Provider capacity",
                    "Wait times", "Network adequacy", "Provider types",
                    "Qualification requirements"
                ],
                "required_documents": [
                    "Provider directory", "Enrollment forms", "Credentialing guidelines",
                    "Network adequacy reports", "Provider capacity data"
                ]
            },
            TopicCategory.SERVICE_DESCRIPTIONS: {
                "keywords": [
                    "services", "treatment", "intervention", "therapy", "behavioral",
                    "developmental", "autism", "ASD", "early intensive", "EIDBI",
                    "scope", "limitations", "covered services"
                ],
                "subtopics": [
                    "Covered EIDBI services", "Service limitations", 
                    "Treatment modalities", "Service intensity",
                    "Duration limits", "Age restrictions", "Coordination with other services"
                ],
                "required_documents": [
                    "Service definitions", "Coverage guidelines", "Treatment protocols",
                    "Service coordination policies"
                ]
            },
            TopicCategory.ELIGIBILITY_ENROLLMENT: {
                "keywords": [
                    "eligibility", "enrollment", "qualify", "requirements", "criteria",
                    "CMDE", "comprehensive multidisciplinary evaluation", "diagnosis",
                    "medical necessity", "age", "income"
                ],
                "subtopics": [
                    "Eligibility criteria", "Age requirements", "Diagnostic requirements",
                    "Income eligibility", "CMDE process", "Enrollment procedures",
                    "Documentation requirements", "Appeal rights"
                ],
                "required_documents": [
                    "Eligibility guidelines", "CMDE requirements", "Enrollment forms",
                    "Income guidelines", "Diagnostic criteria"
                ]
            },
            TopicCategory.POLICIES_COMPLIANCE: {
                "keywords": [
                    "policy", "compliance", "regulations", "requirements", "standards",
                    "quality", "monitoring", "oversight", "audit", "review"
                ],
                "subtopics": [
                    "Program policies", "Compliance requirements", "Quality standards",
                    "Monitoring procedures", "Audit processes", "Corrective actions",
                    "Regulatory requirements"
                ],
                "required_documents": [
                    "Policy manual", "Compliance guidelines", "Quality standards",
                    "Monitoring procedures", "Audit protocols"
                ]
            },
            TopicCategory.TRAINING_SUPPORT: {
                "keywords": [
                    "training", "education", "support", "resources", "materials",
                    "workshops", "certification", "continuing education", "technical assistance"
                ],
                "subtopics": [
                    "Provider training requirements", "Continuing education",
                    "Technical assistance", "Training materials", "Workshops",
                    "Certification programs", "Support resources"
                ],
                "required_documents": [
                    "Training requirements", "Educational materials", "Workshop schedules",
                    "Certification guidelines", "Support resources"
                ]
            },
            TopicCategory.FUNDING_BUDGET: {
                "keywords": [
                    "funding", "budget", "appropriation", "cost", "expenditure",
                    "allocation", "financial", "revenue", "spending"
                ],
                "subtopics": [
                    "Program funding sources", "Budget allocations", "Cost data",
                    "Expenditure reports", "Financial projections", "Funding trends"
                ],
                "required_documents": [
                    "Budget documents", "Funding reports", "Cost analyses",
                    "Financial projections", "Expenditure data"
                ]
            },
            TopicCategory.OUTCOMES_QUALITY: {
                "keywords": [
                    "outcomes", "quality", "measures", "metrics", "performance",
                    "effectiveness", "evaluation", "assessment", "data", "reporting"
                ],
                "subtopics": [
                    "Outcome measures", "Quality metrics", "Performance indicators",
                    "Evaluation methods", "Data collection", "Reporting requirements"
                ],
                "required_documents": [
                    "Outcome measures", "Quality metrics", "Performance reports",
                    "Evaluation protocols", "Data collection procedures"
                ]
            },
            TopicCategory.TECHNOLOGY_TOOLS: {
                "keywords": [
                    "technology", "tools", "systems", "software", "platform",
                    "database", "portal", "application", "digital", "electronic"
                ],
                "subtopics": [
                    "Provider portals", "Data systems", "Electronic tools",
                    "Technology requirements", "System access", "Digital resources"
                ],
                "required_documents": [
                    "System documentation", "User guides", "Technology requirements",
                    "Access procedures", "Digital resources"
                ]
            }
        }

    def _initialize_data_sources(self) -> List[DataSource]:
        """Initialize comprehensive data sources for content collection"""
        return [
            # Minnesota DHS Sources
            DataSource(
                "DHS EIDBI Provider Manual",
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140346",
                "government_pdf", 1
            ),
            DataSource(
                "DHS Medicaid Provider Manual",
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292229",
                "government_pdf", 1
            ),
            DataSource(
                "DHS EIDBI Billing Guide",
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293657",
                "government_pdf", 1
            ),
            DataSource(
                "MHCP Provider Directory",
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_155989",
                "government_web", 2
            ),
            DataSource(
                "Minnesota Legislature EIDBI Statutes",
                "https://www.revisor.mn.gov/statutes/cite/256B.0943",
                "legislation", 1
            ),
            
            # Professional Organizations
            DataSource(
                "ABAI Minnesota Chapter",
                "https://www.abainternational.org/constituents/chapters-and-sigs/chapters/minnesota.aspx",
                "professional_org", 3
            ),
            DataSource(
                "Autism Society of Minnesota",
                "https://ausm.org/resources/",
                "advocacy_org", 3
            ),
            DataSource(
                "The Arc Minnesota",
                "https://arcminnesota.org/resources/",
                "advocacy_org", 3
            ),
            
            # Insurance/Health Plans
            DataSource(
                "Blue Cross Blue Shield MN Provider Directory",
                "https://www.bluecrossmn.com/find-doctor",
                "insurer", 4
            ),
            DataSource(
                "HealthPartners Provider Directory",
                "https://www.healthpartners.com/care/providers/",
                "insurer", 4
            ),
            
            # Academic/Research Sources
            DataSource(
                "PubMed EIDBI Research",
                "https://pubmed.ncbi.nlm.nih.gov/",
                "academic", 5
            ),
            DataSource(
                "Google Scholar EIDBI Studies",
                "https://scholar.google.com/",
                "academic", 5
            ),
            
            # Government Data Portals
            DataSource(
                "Minnesota Open Data Portal",
                "https://mn.gov/data/",
                "open_data", 4
            ),
            DataSource(
                "Data.gov Health Data",
                "https://www.data.gov/",
                "open_data", 4
            )
        ]

    async def perform_comprehensive_audit(self) -> Dict[str, Any]:
        """Perform comprehensive knowledge base audit"""
        logger.info("🔍 Starting comprehensive knowledge base audit...")
        
        audit_start = datetime.now()
        
        # Step 1: Analyze current knowledge base
        current_coverage = await self._analyze_current_knowledge_base()
        
        # Step 2: Assess topic coverage
        coverage_matrix = await self._assess_topic_coverage(current_coverage)
        
        # Step 3: Identify gaps and priorities
        gaps_analysis = await self._identify_gaps_and_priorities(coverage_matrix)
        
        # Step 4: Generate coverage matrix
        coverage_matrix_file = await self._generate_coverage_matrix(coverage_matrix)
        
        # Step 5: Create gap analysis report
        gap_report_file = await self._create_gap_analysis_report(gaps_analysis)
        
        audit_end = datetime.now()
        audit_duration = audit_end - audit_start
        
        audit_results = {
            "audit_id": hashlib.md5(f"{audit_start}".encode()).hexdigest()[:8],
            "timestamp": audit_start.isoformat(),
            "duration_seconds": audit_duration.total_seconds(),
            "total_topics": len(coverage_matrix),
            "fully_covered": len([t for t in coverage_matrix.values() if t.status == CoverageStatus.FULLY_COVERED]),
            "partially_covered": len([t for t in coverage_matrix.values() if t.status == CoverageStatus.PARTIALLY_COVERED]),
            "not_covered": len([t for t in coverage_matrix.values() if t.status == CoverageStatus.NOT_COVERED]),
            "coverage_matrix_file": str(coverage_matrix_file),
            "gap_analysis_file": str(gap_report_file),
            "priority_topics": gaps_analysis["priority_topics"],
            "recommended_sources": gaps_analysis["recommended_sources"]
        }
        
        # Save audit results
        audit_file = self.data_dir / f"audit_results_{audit_start.strftime('%Y%m%d_%H%M%S')}.json"
        with open(audit_file, 'w') as f:
            json.dump(audit_results, f, indent=2, default=str)
        
        logger.info(f"✅ Comprehensive audit completed in {audit_duration.total_seconds():.1f} seconds")
        logger.info(f"📊 Coverage: {audit_results['fully_covered']} fully, {audit_results['partially_covered']} partially, {audit_results['not_covered']} not covered")
        
        return audit_results

    async def _analyze_current_knowledge_base(self) -> Dict[str, Any]:
        """Analyze current knowledge base content"""
        logger.info("📚 Analyzing current knowledge base...")
        
        # Load current knowledge base
        kb_file = Path("local_scraped_data_with_embeddings.jsonl")
        if not kb_file.exists():
            logger.warning("Knowledge base file not found")
            return {"chunks": [], "total_chunks": 0}
        
        chunks = []
        try:
            with open(kb_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            chunks.append(chunk)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error parsing line {line_num}: {e}")
                            continue
        except Exception as e:
            logger.error(f"Error reading knowledge base: {e}")
            return {"chunks": [], "total_chunks": 0}
        
        # Analyze content by topic
        topic_analysis = defaultdict(list)
        for chunk in chunks:
            content = chunk.get('content', '').lower()
            metadata = chunk.get('metadata', {})
            
            # Categorize by topic
            for category, definition in self.topic_definitions.items():
                keyword_matches = sum(1 for keyword in definition['keywords'] if keyword.lower() in content)
                if keyword_matches > 0:
                    topic_analysis[category].append({
                        'chunk_id': chunk.get('id'),
                        'content_preview': content[:200],
                        'keyword_matches': keyword_matches,
                        'source': metadata.get('url', 'unknown'),
                        'title': metadata.get('title', 'unknown')
                    })
        
        analysis_results = {
            "total_chunks": len(chunks),
            "chunks_by_topic": {category.value: len(chunks) for category, chunks in topic_analysis.items()},
            "topic_analysis": {category.value: chunks for category, chunks in topic_analysis.items()},
            "unique_sources": len(set(chunk.get('metadata', {}).get('url', 'unknown') for chunk in chunks)),
            "analysis_date": datetime.now().isoformat()
        }
        
        logger.info(f"📊 Analyzed {len(chunks)} chunks from {analysis_results['unique_sources']} sources")
        
        return analysis_results

    async def _assess_topic_coverage(self, current_analysis: Dict[str, Any]) -> Dict[str, TopicCoverage]:
        """Assess coverage for each topic category"""
        logger.info("🎯 Assessing topic coverage...")
        
        coverage_matrix = {}
        
        for category, definition in self.topic_definitions.items():
            topic_chunks = current_analysis["topic_analysis"].get(category.value, [])
            chunk_count = len(topic_chunks)
            
            # Calculate coverage score based on multiple factors
            coverage_score = self._calculate_coverage_score(category, topic_chunks, definition)
            
            # Determine coverage status
            if coverage_score >= 0.8:
                status = CoverageStatus.FULLY_COVERED
            elif coverage_score >= 0.4:
                status = CoverageStatus.PARTIALLY_COVERED
            else:
                status = CoverageStatus.NOT_COVERED
            
            # Identify missing subtopics
            missing_subtopics = self._identify_missing_subtopics(topic_chunks, definition['subtopics'])
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(category, coverage_score, chunk_count)
            
            # Get key documents
            key_documents = list(set(chunk.get('source', 'unknown') for chunk in topic_chunks[:5]))
            
            coverage_matrix[category.value] = TopicCoverage(
                topic=category.value,
                category=category,
                status=status,
                coverage_score=coverage_score,
                document_count=len(key_documents),
                chunk_count=chunk_count,
                key_documents=key_documents,
                missing_subtopics=missing_subtopics,
                last_updated=datetime.now(),
                priority_score=priority_score,
                notes=f"Coverage based on {chunk_count} chunks from {len(key_documents)} sources"
            )
        
        logger.info(f"📋 Assessed coverage for {len(coverage_matrix)} topic categories")
        
        return coverage_matrix

    def _calculate_coverage_score(self, category: TopicCategory, chunks: List[Dict], definition: Dict) -> float:
        """Calculate coverage score for a topic (0.0 to 1.0)"""
        if not chunks:
            return 0.0
        
        # Factor 1: Keyword coverage (40% weight)
        total_keywords = len(definition['keywords'])
        covered_keywords = set()
        for chunk in chunks:
            content = chunk.get('content_preview', '').lower()
            for keyword in definition['keywords']:
                if keyword.lower() in content:
                    covered_keywords.add(keyword)
        
        keyword_score = len(covered_keywords) / total_keywords if total_keywords > 0 else 0
        
        # Factor 2: Subtopic coverage (40% weight)
        total_subtopics = len(definition['subtopics'])
        covered_subtopics = set()
        for chunk in chunks:
            content = chunk.get('content_preview', '').lower()
            for subtopic in definition['subtopics']:
                # Simple keyword matching for subtopics
                subtopic_words = subtopic.lower().split()
                if any(word in content for word in subtopic_words):
                    covered_subtopics.add(subtopic)
        
        subtopic_score = len(covered_subtopics) / total_subtopics if total_subtopics > 0 else 0
        
        # Factor 3: Content volume (20% weight)
        volume_score = min(len(chunks) / 10, 1.0)  # Normalize to max 10 chunks
        
        # Weighted final score
        final_score = (keyword_score * 0.4) + (subtopic_score * 0.4) + (volume_score * 0.2)
        
        return round(final_score, 3)

    def _identify_missing_subtopics(self, chunks: List[Dict], subtopics: List[str]) -> List[str]:
        """Identify which subtopics are missing from current content"""
        covered_subtopics = set()
        
        for chunk in chunks:
            content = chunk.get('content_preview', '').lower()
            for subtopic in subtopics:
                subtopic_words = subtopic.lower().split()
                if any(word in content for word in subtopic_words):
                    covered_subtopics.add(subtopic)
        
        return [subtopic for subtopic in subtopics if subtopic not in covered_subtopics]

    def _calculate_priority_score(self, category: TopicCategory, coverage_score: float, chunk_count: int) -> float:
        """Calculate priority score for topic enhancement (1-10, higher = more important)"""
        # Base priority by category importance
        category_priorities = {
            TopicCategory.ELIGIBILITY_ENROLLMENT: 10,
            TopicCategory.SERVICE_DESCRIPTIONS: 9,
            TopicCategory.BILLING_CLAIMS: 8,
            TopicCategory.PROVIDER_NETWORK: 8,
            TopicCategory.POLICIES_COMPLIANCE: 7,
            TopicCategory.TRAINING_SUPPORT: 6,
            TopicCategory.OUTCOMES_QUALITY: 5,
            TopicCategory.FUNDING_BUDGET: 4,
            TopicCategory.TECHNOLOGY_TOOLS: 3
        }
        
        base_priority = category_priorities.get(category, 5)
        
        # Adjust based on coverage gap (higher gap = higher priority)
        gap_multiplier = 1.0 - coverage_score
        
        # Adjust based on content volume (less content = higher priority)
        volume_multiplier = 1.0 - min(chunk_count / 20, 0.5)
        
        final_priority = base_priority * (1 + gap_multiplier + volume_multiplier)
        
        return round(min(final_priority, 10.0), 2)

    async def _identify_gaps_and_priorities(self, coverage_matrix: Dict[str, TopicCoverage]) -> Dict[str, Any]:
        """Identify gaps and prioritize topics for enhancement"""
        logger.info("🎯 Identifying gaps and priorities...")
        
        # Sort topics by priority score
        priority_topics = sorted(
            coverage_matrix.values(),
            key=lambda x: x.priority_score,
            reverse=True
        )
        
        # Identify high-priority gaps
        high_priority_gaps = [
            topic for topic in priority_topics 
            if topic.priority_score >= 7.0 and topic.status != CoverageStatus.FULLY_COVERED
        ]
        
        # Recommend data sources for each gap
        source_recommendations = {}
        for topic in high_priority_gaps:
            recommended_sources = self._recommend_sources_for_topic(topic.category)
            source_recommendations[topic.topic] = recommended_sources
        
        gaps_analysis = {
            "total_gaps": len([t for t in coverage_matrix.values() if t.status != CoverageStatus.FULLY_COVERED]),
            "high_priority_gaps": len(high_priority_gaps),
            "priority_topics": [
                {
                    "topic": topic.topic,
                    "status": topic.status.value,
                    "coverage_score": topic.coverage_score,
                    "priority_score": topic.priority_score,
                    "missing_subtopics": topic.missing_subtopics[:5],  # Top 5
                    "chunk_count": topic.chunk_count
                }
                for topic in priority_topics[:10]  # Top 10 priorities
            ],
            "recommended_sources": source_recommendations,
            "analysis_date": datetime.now().isoformat()
        }
        
        logger.info(f"🎯 Identified {len(high_priority_gaps)} high-priority gaps")
        
        return gaps_analysis

    def _recommend_sources_for_topic(self, category: TopicCategory) -> List[Dict[str, Any]]:
        """Recommend data sources for a specific topic category"""
        # Map categories to relevant source types
        source_mapping = {
            TopicCategory.BILLING_CLAIMS: ["government_pdf", "government_web"],
            TopicCategory.PROVIDER_NETWORK: ["government_web", "insurer", "professional_org"],
            TopicCategory.SERVICE_DESCRIPTIONS: ["government_pdf", "professional_org", "academic"],
            TopicCategory.ELIGIBILITY_ENROLLMENT: ["government_pdf", "government_web"],
            TopicCategory.POLICIES_COMPLIANCE: ["government_pdf", "legislation"],
            TopicCategory.TRAINING_SUPPORT: ["professional_org", "advocacy_org", "academic"],
            TopicCategory.FUNDING_BUDGET: ["government_pdf", "open_data", "legislation"],
            TopicCategory.OUTCOMES_QUALITY: ["academic", "government_pdf", "open_data"],
            TopicCategory.TECHNOLOGY_TOOLS: ["government_web", "professional_org"]
        }
        
        relevant_types = source_mapping.get(category, ["government_pdf", "government_web"])
        
        recommended = []
        for source in self.data_sources:
            if source.source_type in relevant_types:
                recommended.append({
                    "name": source.name,
                    "url": source.url,
                    "type": source.source_type,
                    "priority": source.priority
                })
        
        # Sort by priority
        recommended.sort(key=lambda x: x["priority"])
        
        return recommended[:5]  # Top 5 recommendations

    async def _generate_coverage_matrix(self, coverage_matrix: Dict[str, TopicCoverage]) -> Path:
        """Generate coverage matrix CSV file"""
        logger.info("📊 Generating coverage matrix...")
        
        # Prepare data for CSV
        csv_data = []
        for topic_name, coverage in coverage_matrix.items():
            csv_data.append({
                "Topic": coverage.topic,
                "Category": coverage.category.value,
                "Coverage Status": coverage.status.value,
                "Coverage Score": f"{coverage.coverage_score:.3f}",
                "Priority Score": f"{coverage.priority_score:.2f}",
                "Document Count": coverage.document_count,
                "Chunk Count": coverage.chunk_count,
                "Key Documents": "; ".join(coverage.key_documents[:3]),
                "Missing Subtopics Count": len(coverage.missing_subtopics),
                "Top Missing Subtopics": "; ".join(coverage.missing_subtopics[:3]),
                "Last Updated": coverage.last_updated.strftime("%Y-%m-%d %H:%M"),
                "Notes": coverage.notes
            })
        
        # Sort by priority score
        csv_data.sort(key=lambda x: float(x["Priority Score"]), reverse=True)
        
        # Save to CSV
        csv_file = self.data_dir / f"coverage_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if csv_data:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
        
        logger.info(f"📊 Coverage matrix saved to {csv_file}")
        
        return csv_file

    async def _create_gap_analysis_report(self, gaps_analysis: Dict[str, Any]) -> Path:
        """Create detailed gap analysis report"""
        logger.info("📝 Creating gap analysis report...")
        
        report_content = f"""# EIDBI Knowledge Base Gap Analysis Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Total Topics Analyzed:** {len(self.topic_definitions)}
- **Topics with Gaps:** {gaps_analysis['total_gaps']}
- **High-Priority Gaps:** {gaps_analysis['high_priority_gaps']}

## Priority Topics for Enhancement

"""
        
        for i, topic in enumerate(gaps_analysis['priority_topics'], 1):
            report_content += f"""### {i}. {topic['topic']}

- **Status:** {topic['status']}
- **Coverage Score:** {topic['coverage_score']:.3f}/1.000
- **Priority Score:** {topic['priority_score']:.2f}/10.0
- **Current Chunks:** {topic['chunk_count']}
- **Missing Subtopics:** {len(topic.get('missing_subtopics', []))}

**Key Missing Areas:**
"""
            for subtopic in topic.get('missing_subtopics', [])[:5]:
                report_content += f"- {subtopic}\n"
            
            report_content += "\n"
        
        report_content += """## Recommended Data Sources

"""
        
        for topic, sources in gaps_analysis['recommended_sources'].items():
            report_content += f"""### {topic}

"""
            for source in sources:
                report_content += f"- **{source['name']}** ({source['type']}) - Priority {source['priority']}\n"
                report_content += f"  URL: {source['url']}\n\n"
        
        report_content += f"""## Next Steps

1. **Immediate Actions (High Priority)**
   - Focus on topics with priority score ≥ 8.0
   - Target sources with priority 1-2 for data collection
   - Address missing subtopics in eligibility and service descriptions

2. **Medium-term Actions**
   - Enhance partially covered topics
   - Expand provider network information
   - Improve billing and claims documentation

3. **Long-term Actions**
   - Establish automated data refresh pipelines
   - Monitor coverage improvements
   - Regular audit cycles (monthly recommended)

## Methodology

This analysis evaluated {len(self.topic_definitions)} topic categories using:
- Keyword coverage analysis (40% weight)
- Subtopic coverage analysis (40% weight)  
- Content volume assessment (20% weight)

Coverage scores range from 0.0 (no coverage) to 1.0 (full coverage).
Priority scores range from 1.0 (low priority) to 10.0 (highest priority).

---
*Report generated by EIDBI Knowledge Base Audit System*
"""
        
        # Save report
        report_file = self.data_dir / f"gap_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📝 Gap analysis report saved to {report_file}")
        
        return report_file

    async def source_missing_content(self, priority_topics: List[str], max_sources: int = 5) -> Dict[str, Any]:
        """Source and process content for missing or partial topics"""
        logger.info(f"🔍 Sourcing content for {len(priority_topics)} priority topics...")
        
        sourcing_start = datetime.now()
        collected_content = []
        source_logs = []
        
        # Get recommended sources for priority topics
        target_sources = []
        for topic in priority_topics:
            if topic in self.coverage_matrix:
                category = self.coverage_matrix[topic].category
                recommended = self._recommend_sources_for_topic(category)
                target_sources.extend(recommended[:2])  # Top 2 per topic
        
        # Remove duplicates and limit
        unique_sources = []
        seen_urls = set()
        for source in target_sources:
            if source['url'] not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(source['url'])
        
        target_sources = unique_sources[:max_sources]
        
        # Process each source
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for source in target_sources:
                try:
                    logger.info(f"Processing source: {source['name']}")
                    
                    content_items = await self._extract_content_from_source(session, source)
                    collected_content.extend(content_items)
                    
                    source_logs.append({
                        "source": source['name'],
                        "url": source['url'],
                        "status": "success",
                        "items_collected": len(content_items),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing {source['name']}: {e}")
                    source_logs.append({
                        "source": source['name'],
                        "url": source['url'],
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Process and integrate collected content
        if collected_content:
            integration_result = await self._integrate_new_content(collected_content)
        else:
            integration_result = {"status": "no_content", "integrated_items": 0}
        
        sourcing_end = datetime.now()
        sourcing_duration = sourcing_end - sourcing_start
        
        sourcing_results = {
            "sourcing_id": hashlib.md5(f"{sourcing_start}".encode()).hexdigest()[:8],
            "timestamp": sourcing_start.isoformat(),
            "duration_seconds": sourcing_duration.total_seconds(),
            "target_topics": priority_topics,
            "sources_processed": len(target_sources),
            "content_items_collected": len(collected_content),
            "integration_result": integration_result,
            "source_logs": source_logs,
            "success_rate": len([log for log in source_logs if log["status"] == "success"]) / len(source_logs) if source_logs else 0
        }
        
        # Save sourcing results
        sourcing_file = self.data_dir / f"sourcing_results_{sourcing_start.strftime('%Y%m%d_%H%M%S')}.json"
        with open(sourcing_file, 'w') as f:
            json.dump(sourcing_results, f, indent=2, default=str)
        
        logger.info(f"✅ Content sourcing completed: {len(collected_content)} items collected from {len(target_sources)} sources")
        
        return sourcing_results

    async def _extract_content_from_source(self, session: aiohttp.ClientSession, source: Dict[str, Any]) -> List[ContentItem]:
        """Extract content from a specific data source"""
        content_items = []
        
        try:
            # Simple web scraping for demonstration
            # In production, this would use specialized extractors for different source types
            
            async with session.get(source['url']) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # Basic text extraction (simplified)
                    # Remove HTML tags
                    import re
                    text_content = re.sub(r'<[^>]+>', ' ', html_content)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                    
                    if len(text_content) > 500:  # Minimum content threshold
                        # Chunk content into manageable pieces
                        chunks = self._chunk_content(text_content, source['name'])
                        
                        for i, chunk in enumerate(chunks):
                            content_item = ContentItem(
                                id=hashlib.md5(f"{source['url']}_{i}".encode()).hexdigest(),
                                title=f"{source['name']} - Chunk {i+1}",
                                content=chunk,
                                source=source['name'],
                                url=source['url'],
                                category=self._categorize_content(chunk),
                                extracted_date=datetime.now(),
                                confidence_score=0.8,  # Default confidence
                                metadata={
                                    "source_type": source['type'],
                                    "chunk_index": i,
                                    "total_chunks": len(chunks)
                                }
                            )
                            content_items.append(content_item)
                
        except Exception as e:
            logger.error(f"Error extracting from {source['name']}: {e}")
        
        return content_items

    def _chunk_content(self, content: str, source_name: str, chunk_size: int = 1000) -> List[str]:
        """Chunk content into manageable pieces"""
        # Simple sentence-aware chunking
        sentences = content.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    def _categorize_content(self, content: str) -> TopicCategory:
        """Categorize content into topic categories"""
        content_lower = content.lower()
        
        # Score each category based on keyword matches
        category_scores = {}
        for category, definition in self.topic_definitions.items():
            score = sum(1 for keyword in definition['keywords'] if keyword.lower() in content_lower)
            category_scores[category] = score
        
        # Return category with highest score, or default
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            if category_scores[best_category] > 0:
                return best_category
        
        return TopicCategory.SERVICE_DESCRIPTIONS  # Default category

    async def _integrate_new_content(self, content_items: List[ContentItem]) -> Dict[str, Any]:
        """Integrate new content into the knowledge base"""
        logger.info(f"🔄 Integrating {len(content_items)} new content items...")
        
        # Prepare content for integration
        integration_data = []
        for item in content_items:
            integration_data.append({
                "id": item.id,
                "content": item.content,
                "metadata": {
                    "title": item.title,
                    "source": item.source,
                    "url": item.url,
                    "category": item.category.value,
                    "extracted_date": item.extracted_date.isoformat(),
                    "confidence_score": item.confidence_score,
                    **item.metadata
                }
            })
        
        # Save new content to integration file
        integration_file = self.data_dir / f"new_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        with open(integration_file, 'w', encoding='utf-8') as f:
            for item in integration_data:
                f.write(json.dumps(item, default=str) + '\n')
        
        logger.info(f"💾 New content saved to {integration_file}")
        
        return {
            "status": "success",
            "integrated_items": len(content_items),
            "integration_file": str(integration_file),
            "categories_updated": list(set(item.category.value for item in content_items))
        }

    async def continuous_improvement_cycle(self, cycle_interval_hours: int = 24) -> Dict[str, Any]:
        """Run continuous improvement cycle"""
        logger.info(f"🔄 Starting continuous improvement cycle (interval: {cycle_interval_hours}h)")
        
        cycle_start = datetime.now()
        
        # Step 1: Perform audit
        audit_results = await self.perform_comprehensive_audit()
        
        # Step 2: Identify high-priority gaps
        high_priority_topics = [
            topic["topic"] for topic in audit_results.get("priority_topics", [])
            if topic.get("priority_score", 0) >= 7.0
        ]
        
        # Step 3: Source missing content
        if high_priority_topics:
            sourcing_results = await self.source_missing_content(high_priority_topics[:5])
        else:
            sourcing_results = {"status": "no_gaps", "content_items_collected": 0}
        
        # Step 4: Generate progress report
        progress_report = await self._generate_progress_report(audit_results, sourcing_results)
        
        cycle_end = datetime.now()
        cycle_duration = cycle_end - cycle_start
        
        cycle_results = {
            "cycle_id": hashlib.md5(f"{cycle_start}".encode()).hexdigest()[:8],
            "timestamp": cycle_start.isoformat(),
            "duration_seconds": cycle_duration.total_seconds(),
            "audit_results": audit_results,
            "sourcing_results": sourcing_results,
            "progress_report": str(progress_report),
            "next_cycle": (cycle_start + timedelta(hours=cycle_interval_hours)).isoformat()
        }
        
        # Save cycle results
        cycle_file = self.data_dir / f"improvement_cycle_{cycle_start.strftime('%Y%m%d_%H%M%S')}.json"
        with open(cycle_file, 'w') as f:
            json.dump(cycle_results, f, indent=2, default=str)
        
        logger.info(f"✅ Improvement cycle completed in {cycle_duration.total_seconds():.1f} seconds")
        
        return cycle_results

    async def _generate_progress_report(self, audit_results: Dict[str, Any], sourcing_results: Dict[str, Any]) -> Path:
        """Generate progress and changelog report"""
        logger.info("📈 Generating progress report...")
        
        report_content = f"""# EIDBI Knowledge Base Progress Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Audit Summary

- **Audit ID:** {audit_results.get('audit_id')}
- **Total Topics:** {audit_results.get('total_topics')}
- **Fully Covered:** {audit_results.get('fully_covered')}
- **Partially Covered:** {audit_results.get('partially_covered')}
- **Not Covered:** {audit_results.get('not_covered')}

## Content Sourcing Results

- **Sourcing ID:** {sourcing_results.get('sourcing_id', 'N/A')}
- **Sources Processed:** {sourcing_results.get('sources_processed', 0)}
- **Content Items Collected:** {sourcing_results.get('content_items_collected', 0)}
- **Success Rate:** {sourcing_results.get('success_rate', 0):.1%}

## Priority Actions Taken

"""
        
        if sourcing_results.get('content_items_collected', 0) > 0:
            report_content += f"""### Content Collection
- Successfully collected {sourcing_results['content_items_collected']} new content items
- Processed {sourcing_results['sources_processed']} data sources
- Integration status: {sourcing_results.get('integration_result', {}).get('status', 'unknown')}

"""
        
        report_content += f"""## Recommendations for Next Cycle

1. **High Priority:**
   - Continue focusing on topics with priority score ≥ 8.0
   - Address any failed source connections
   - Monitor integration success

2. **Medium Priority:**
   - Expand coverage for partially covered topics
   - Explore additional data sources
   - Improve content quality scoring

3. **Ongoing:**
   - Maintain regular audit cycles
   - Monitor user query patterns for gap identification
   - Update source reliability metrics

## Files Generated

- **Coverage Matrix:** {audit_results.get('coverage_matrix_file', 'N/A')}
- **Gap Analysis:** {audit_results.get('gap_analysis_file', 'N/A')}
- **New Content:** {sourcing_results.get('integration_result', {}).get('integration_file', 'N/A')}

---
*Generated by EIDBI Knowledge Base Audit System*
"""
        
        # Save progress report
        report_file = self.data_dir / f"progress_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📈 Progress report saved to {report_file}")
        
        return report_file

async def main():
    """Main execution function"""
    print("🚀 EIDBI Knowledge Base Audit and Enhancement System")
    print("=" * 60)
    
    # Initialize auditor
    auditor = KnowledgeBaseAuditor()
    
    # Perform comprehensive audit
    print("\n1️⃣ Performing Comprehensive Audit...")
    audit_results = await auditor.perform_comprehensive_audit()
    
    print(f"\n📊 Audit Results:")
    print(f"   • Total Topics: {audit_results['total_topics']}")
    print(f"   • Fully Covered: {audit_results['fully_covered']}")
    print(f"   • Partially Covered: {audit_results['partially_covered']}")
    print(f"   • Not Covered: {audit_results['not_covered']}")
    print(f"   • Coverage Matrix: {audit_results['coverage_matrix_file']}")
    print(f"   • Gap Analysis: {audit_results['gap_analysis_file']}")
    
    # Source missing content for high-priority topics
    high_priority_topics = [
        topic["topic"] for topic in audit_results.get("priority_topics", [])
        if topic.get("priority_score", 0) >= 7.0
    ]
    
    if high_priority_topics:
        print(f"\n2️⃣ Sourcing Content for {len(high_priority_topics)} High-Priority Topics...")
        sourcing_results = await auditor.source_missing_content(high_priority_topics[:3])
        
        print(f"\n📥 Sourcing Results:")
        print(f"   • Sources Processed: {sourcing_results['sources_processed']}")
        print(f"   • Content Items Collected: {sourcing_results['content_items_collected']}")
        print(f"   • Success Rate: {sourcing_results['success_rate']:.1%}")
    else:
        print("\n2️⃣ No high-priority gaps identified - skipping content sourcing")
        sourcing_results = {"status": "no_gaps"}
    
    # Run improvement cycle
    print("\n3️⃣ Running Continuous Improvement Cycle...")
    cycle_results = await auditor.continuous_improvement_cycle()
    
    print(f"\n🔄 Cycle Results:")
    print(f"   • Cycle ID: {cycle_results['cycle_id']}")
    print(f"   • Duration: {cycle_results['duration_seconds']:.1f} seconds")
    print(f"   • Progress Report: {cycle_results['progress_report']}")
    print(f"   • Next Cycle: {cycle_results['next_cycle']}")
    
    print("\n✅ Knowledge Base Audit and Enhancement Complete!")
    print(f"📁 All results saved to: {auditor.data_dir}")

if __name__ == "__main__":
    asyncio.run(main()) 