#!/usr/bin/env python3
"""
Extract Detailed EIDBI Training Requirements

This script extracts and structures the specific mandated training requirements
from the DHS provider training documentation.

Author: AI Assistant
Date: January 27, 2025
"""

import json
from datetime import datetime
from pathlib import Path
import hashlib

def extract_training_requirements():
    """Extract and structure the detailed training requirements"""
    
    # Based on the comprehensive DHS Provider Training Document content
    training_requirements = {
        "metadata": {
            "source": "DHS Provider Training Document",
            "source_url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292819",
            "extraction_date": datetime.now().isoformat(),
            "version": "2024-12-11"
        },
        "requirements": {
            "all_providers": {
                "description": "Required training for ALL EIDBI providers",
                "trainings": [
                    {
                        "name": "Cultural Responsiveness in Autism Spectrum Disorder (ASD) Services",
                        "course_code": "ASDCULTURE",
                        "platform": "TrainLink",
                        "duration": "Not specified",
                        "format": "Online",
                        "certificate_required": True,
                        "frequency": "One-time requirement",
                        "description": "Helps providers increase understanding of culturally responsive practices when providing services to people with ASD or related conditions"
                    },
                    {
                        "name": "DHS Vulnerable Adults Mandated Reporting (VAMR) Online Course and Exam",
                        "platform": "DHS",
                        "format": "Online course with exam",
                        "certificate_required": True,
                        "frequency": "One-time requirement (but DHS recommends staying informed about updates)",
                        "description": "Legal obligations for mandated reporting of vulnerable adults"
                    },
                    {
                        "name": "Minnesota Child Welfare Training Academy Mandated Reporting Training",
                        "platform": "Minnesota Child Welfare Training Academy",
                        "format": "Online",
                        "certificate_required": True,
                        "frequency": "One-time requirement (but DHS recommends staying informed about updates)",
                        "description": "Legal obligations for mandated reporting of child welfare concerns"
                    }
                ]
            },
            "level_iii_providers": {
                "description": "Additional required training for Level III providers",
                "trainings": [
                    {
                        "name": "ASD Strategies in Action",
                        "platform": "Autism Certification Center",
                        "duration": "90-minute introduction + one age-specific module",
                        "format": "Online video-based learning series",
                        "modules": [
                            "90-minute introduction (Many Faces of Autism)",
                            "Toddler and preschool age module",
                            "School age module", 
                            "Transition age module"
                        ],
                        "requirement": "Must complete introduction + at least one age-specific module",
                        "features": ["Closed captioning", "Interactive transcripts", "Comprehension checks", "Continuing education credit", "Note-taking tool", "Searchable glossary"],
                        "exception": "Not required if provider completes behavior assessment and planning with evidence-based interventions online training or successfully completes RBT training",
                        "certificate_required": True,
                        "frequency": "One-time requirement"
                    },
                    {
                        "name": "EIDBI 101: Overview of the Benefit",
                        "course_code": "EIDBI101_P",
                        "platform": "TrainLink",
                        "format": "Online",
                        "topics": ["EIDBI benefit overview", "Provider eligibility", "Covered/non-covered services", "Required training", "SIRS", "Billing and authorizations"],
                        "certificate_required": True,
                        "frequency": "One-time requirement"
                    }
                ]
            },
            "variance_providers": {
                "description": "Additional requirements for providers enrolled under certain variances",
                "applies_to": ["Level I provider variance one", "Level II provider variance two"],
                "trainings": [
                    {
                        "name": "ASD Strategies in Action",
                        "details": "Same as Level III requirements"
                    },
                    {
                        "name": "EIDBI 101: Overview of the Benefit",
                        "details": "Same as Level III requirements"
                    }
                ]
            },
            "recommended_trainings": {
                "description": "Recommended but not required trainings",
                "all_providers": [
                    {
                        "name": "ASD Strategies in Action",
                        "recommendation": "Especially helpful for providers on variances or with limited clinical experience"
                    },
                    {
                        "name": "EIDBI 101: Overview of the Benefit"
                    },
                    {
                        "name": "Coordinating Services and Supports for a Child with ASD or Related Conditions",
                        "course_code": "Not specified",
                        "description": "Helps professionals make accurate referrals based on person's and family's needs"
                    },
                    {
                        "name": "Telehealth for Early Intervention",
                        "course_code": "EIDBI_Tele",
                        "topics": ["Benefits and barriers of telehealth", "Services offered via telehealth", "Session preparation", "Best-practice guidelines"]
                    }
                ],
                "cmde_itp_providers": [
                    {
                        "name": "CMDE and ITP Overview Training",
                        "course_code": "ASDCMDEITP",
                        "recommended_for": "CMDE providers, QSPs, and any providers who help complete the CMDE or ITP",
                        "topics": ["CMDE overview", "ITP overview", "Step-by-step instructions", "Information gathering strategies"]
                    }
                ]
            }
        },
        "compliance": {
            "timeline": {
                "requirement": "Within 6 months of hiring date",
                "note": "DHS requires each individual EIDBI provider to complete their required training(s) within six months of their hiring date"
            },
            "frequency": {
                "requirement": "One-time completion",
                "note": "Providers are only required to take the EIDBI required trainings one time. If a provider transitions to a new agency, DHS does not require them to complete the trainings again as long as they have maintained documentation"
            },
            "documentation": {
                "requirement": "Maintain in provider file",
                "details": "The EIDBI provider agency must document each provider's training history, including start and completion dates of orientation and additional EIDBI trainings. The agency must store this information in the provider's file"
            }
        },
        "continuing_education": {
            "description": "DHS encourages ongoing professional development",
            "recommendations": [
                "Participate in relevant ongoing training (workshops, webinars, conferences)",
                "Stay updated on policies",
                "Pursue advanced training and certification",
                "Engage in peer networking and learning"
            ]
        }
    }
    
    # Save the structured requirements
    output_dir = Path("data/training_requirements")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"detailed_training_requirements_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_requirements, f, indent=2)
    
    # Create knowledge base entries
    kb_entries = []
    
    # Entry 1: Overview of all requirements
    kb_entries.append({
        "id": f"training_req_{hashlib.md5('overview'.encode()).hexdigest()}",
        "title": "EIDBI Provider Training Requirements - Complete Overview",
        "content": """Minnesota EIDBI Provider Training Requirements:

ALL PROVIDERS MUST COMPLETE:
1. Cultural Responsiveness in Autism Spectrum Disorder (ASD) Services (TrainLink course: ASDCULTURE)
2. DHS Vulnerable Adults Mandated Reporting (VAMR) Online Course and Exam
3. Minnesota Child Welfare Training Academy Mandated Reporting Training

LEVEL III PROVIDERS ADDITIONAL REQUIREMENTS:
1. ASD Strategies in Action (90-minute introduction + one age-specific module)
2. EIDBI 101: Overview of the Benefit (TrainLink course: EIDBI101_P)

VARIANCE PROVIDERS (Level I variance one, Level II variance two):
Must also complete the Level III additional requirements above.

TIMELINE: All trainings must be completed within 6 months of hiring date.
FREQUENCY: One-time requirement - providers who change agencies do not need to retake if documented.
DOCUMENTATION: Agencies must maintain completion certificates in provider files.""",
        "source": "DHS Provider Training Document",
        "source_url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292819",
        "category": "Training Requirements",
        "topic": "Mandated Training Overview",
        "metadata": {
            "extraction_date": datetime.now().isoformat(),
            "mandated": True,
            "provider_levels": ["All", "Level I", "Level II", "Level III"],
            "last_updated": "2024-12-11"
        },
        "embedding": generate_embedding("training requirements mandated eidbi providers minnesota"),
        "last_updated": datetime.now().isoformat()
    })
    
    # Entry 2: Detailed requirements by provider level
    for level, data in training_requirements["requirements"].items():
        if level != "recommended_trainings":
            content = f"{data['description']}\n\n"
            for training in data.get('trainings', []):
                content += f"• {training['name']}\n"
                if 'course_code' in training:
                    content += f"  - Course Code: {training['course_code']}\n"
                if 'platform' in training:
                    content += f"  - Platform: {training['platform']}\n"
                if 'duration' in training:
                    content += f"  - Duration: {training['duration']}\n"
                if 'modules' in training:
                    content += f"  - Modules: {', '.join(training['modules'])}\n"
                content += "\n"
                
            kb_entries.append({
                "id": f"training_req_{hashlib.md5(level.encode()).hexdigest()}",
                "title": f"EIDBI Training Requirements - {level.replace('_', ' ').title()}",
                "content": content,
                "source": "DHS Provider Training Document",
                "source_url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292819",
                "category": "Training Requirements",
                "topic": f"{level.replace('_', ' ').title()} Requirements",
                "metadata": {
                    "extraction_date": datetime.now().isoformat(),
                    "mandated": True,
                    "provider_level": level
                },
                "embedding": generate_embedding(f"training requirements {level}"),
                "last_updated": datetime.now().isoformat()
            })
    
    # Save KB entries
    kb_file = output_dir / f"training_requirements_kb_entries_{timestamp}.jsonl"
    with open(kb_file, 'w', encoding='utf-8') as f:
        for entry in kb_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"✅ Extracted detailed training requirements")
    print(f"📁 Saved to: {output_file}")
    print(f"📚 Created {len(kb_entries)} knowledge base entries: {kb_file}")
    
    return training_requirements, kb_entries

def generate_embedding(text):
    """Generate mock embedding for text"""
    hash_val = hashlib.md5(text.encode()).hexdigest()
    embedding = []
    for i in range(0, min(len(hash_val), 768), 2):
        val = int(hash_val[i:i+2], 16) / 255.0
        embedding.append(val)
    while len(embedding) < 768:
        embedding.append(0.0)
    return embedding[:768]

if __name__ == "__main__":
    extract_training_requirements() 