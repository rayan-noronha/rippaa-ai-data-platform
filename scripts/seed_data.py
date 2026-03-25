"""Synthetic data generator for the RIPPAA AI Data Platform.

Generates realistic enterprise documents across 4 domains:
- Insurance: policy wordings, claims reports, underwriting guidelines
- Financial: regulatory filings, compliance docs, risk assessments
- Government: council policies, procurement guidelines, internal memos
- Enterprise: HR policies, IT security docs, vendor contracts

Intentionally includes data quality issues to test pipeline robustness:
- PII leakage (names, emails, ABNs, Medicare numbers)
- Missing fields and inconsistent formats
- Duplicate documents with variant metadata
- Stale/outdated documents
- Conflicting information across documents
- Malformed files (corrupted CSV, misaligned data)

Usage:
    python scripts/seed_data.py [--output-dir data/synthetic] [--count 60]
"""

import argparse
import csv
import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from faker import Faker

# Seed for reproducibility — same data every run
SEED = 42
random.seed(SEED)
fake = Faker("en_AU")  # Australian locale for realistic Aussie data
Faker.seed(SEED)


# ─────────────────────────────────────────────
# Australian-specific PII generators
# ─────────────────────────────────────────────


def generate_abn() -> str:
    """Generate a fake but realistic-looking Australian Business Number."""
    return f"{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}"


def generate_medicare() -> str:
    """Generate a fake Medicare number."""
    return f"{random.randint(2000, 6999)} {random.randint(10000, 99999)} {random.randint(1, 9)}"


def generate_tfn() -> str:
    """Generate a fake Tax File Number."""
    return f"{random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}"


def generate_phone_au() -> str:
    """Generate a fake Australian phone number."""
    return f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"


# ─────────────────────────────────────────────
# Insurance Domain Documents
# ─────────────────────────────────────────────


def generate_insurance_policy(doc_id: int) -> dict:
    """Generate a synthetic insurance policy wording document."""
    policy_types = ["Home & Contents", "Motor Vehicle", "CTP", "Landlord", "Business Pack", "Travel"]
    policy_type = random.choice(policy_types)
    insurer = random.choice(["RAA Insurance", "AAMI", "Suncorp", "Allianz", "IAG", "QBE"])
    effective_date = fake.date_between(start_date="-3y", end_date="today")
    expiry_date = effective_date + timedelta(days=365)

    # Intentional PII leakage — real-looking names and contact details embedded in policy text
    policyholder = fake.name()
    email = fake.email()
    phone = generate_phone_au()
    address = fake.address()

    content = f"""
{insurer} — {policy_type} Insurance Policy

POLICY DOCUMENT
Policy Number: {insurer[:3].upper()}-{random.randint(100000, 999999)}
Effective Date: {effective_date.strftime('%d/%m/%Y')}
Expiry Date: {expiry_date.strftime('%d/%m/%Y')}

POLICYHOLDER DETAILS
Name: {policyholder}
Email: {email}
Phone: {phone}
Address: {address}

SECTION 1: COVERAGE SUMMARY

This {policy_type} policy provides coverage for the following:

1.1 Building Cover
Maximum sum insured: ${random.randint(300, 900) * 1000:,}
Excess: ${random.choice([500, 750, 1000, 1500]):,}

1.2 Contents Cover
Maximum sum insured: ${random.randint(50, 200) * 1000:,}
Excess: ${random.choice([200, 500, 750]):,}

1.3 Liability Cover
Public liability: ${random.choice([10, 20, 30])} million
Legal costs included up to $50,000

SECTION 2: EXCLUSIONS

This policy does NOT cover:
- Damage caused by flood (unless Flood Cover extension purchased)
- Wear and tear or gradual deterioration
- Damage caused by pests, insects, or vermin
- Loss or damage to motor vehicles (covered under separate Motor Vehicle policy)
- Pre-existing damage not disclosed at time of application
- Acts of war or terrorism (except as required by law)

SECTION 3: CLAIMS PROCESS

To make a claim:
1. Contact our claims team on 1300 {random.randint(100, 999)} {random.randint(100, 999)}
2. Provide your policy number and details of the incident
3. A claims assessor will be assigned within 2 business days
4. You may be required to obtain quotes for repair or replacement

Claims must be lodged within 30 days of the incident.

SECTION 4: PREMIUM

Annual premium: ${random.randint(800, 3500):,}.{random.randint(0, 99):02d}
Government charges: ${random.randint(50, 200):,}.{random.randint(0, 99):02d}
GST: Included
Payment frequency: {random.choice(['Annual', 'Monthly', 'Quarterly'])}

This policy is underwritten by {insurer} ABN {generate_abn()}.
Australian Financial Services Licence No. {random.randint(200000, 500000)}.

IMPORTANT: This document contains personal information about {policyholder}.
Please handle in accordance with the Privacy Act 1988 (Cth).
"""

    return {
        "id": str(uuid4()),
        "filename": f"policy_{insurer.lower().replace(' ', '_')}_{policy_type.lower().replace(' & ', '_').replace(' ', '_')}_{doc_id:03d}.txt",
        "source_domain": "insurance",
        "file_type": "txt",
        "content": content.strip(),
        "metadata": {
            "policy_type": policy_type,
            "insurer": insurer,
            "effective_date": effective_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "policyholder": policyholder,
        },
    }


def generate_claims_report(doc_id: int) -> dict:
    """Generate a synthetic insurance claims report as CSV data."""
    num_claims = random.randint(15, 40)
    claims = []
    claim_types = ["Property Damage", "Theft", "Water Damage", "Storm Damage", "Fire", "Liability", "Motor Accident"]
    statuses = ["Open", "Under Assessment", "Approved", "Paid", "Declined", "Withdrawn"]

    for i in range(num_claims):
        claim_date = fake.date_between(start_date="-2y", end_date="today")
        settlement_date = claim_date + timedelta(days=random.randint(7, 120)) if random.random() > 0.3 else None

        claim = {
            "claim_id": f"CLM-{random.randint(100000, 999999)}",
            "policy_number": f"RAA-{random.randint(100000, 999999)}",
            "claimant_name": fake.name(),  # Intentional PII
            "claimant_email": fake.email(),  # Intentional PII
            "claimant_phone": generate_phone_au(),  # Intentional PII
            "claim_type": random.choice(claim_types),
            "claim_date": claim_date.strftime("%d/%m/%Y"),
            "description": fake.sentence(nb_words=12),
            "claimed_amount": round(random.uniform(500, 75000), 2),
            "assessed_amount": round(random.uniform(200, 60000), 2) if random.random() > 0.2 else "",
            "status": random.choice(statuses),
            "settlement_date": settlement_date.strftime("%m-%d-%Y") if settlement_date else "",  # Intentional format inconsistency: MM-DD-YYYY vs DD/MM/YYYY
            "assessor": fake.name() if random.random() > 0.15 else "",  # Intentional missing field
        }

        # Intentional: some rows have missing claimed_amount
        if random.random() < 0.05:
            claim["claimed_amount"] = ""

        claims.append(claim)

    # Intentional: add a duplicate claim with slightly different metadata
    if claims:
        duplicate = claims[0].copy()
        duplicate["claimant_email"] = duplicate["claimant_email"].upper()  # Same person, different case
        duplicate["status"] = "Under Assessment"  # Different status for same claim
        claims.append(duplicate)

    return {
        "id": str(uuid4()),
        "filename": f"claims_report_q{random.randint(1, 4)}_{random.randint(2023, 2025)}_{doc_id:03d}.csv",
        "source_domain": "insurance",
        "file_type": "csv",
        "content": claims,
        "metadata": {
            "report_type": "claims_register",
            "total_claims": len(claims),
            "period": f"Q{random.randint(1, 4)} {random.randint(2023, 2025)}",
        },
    }


def generate_underwriting_guidelines(doc_id: int) -> dict:
    """Generate synthetic underwriting guidelines document."""
    risk_category = random.choice(["Residential Property", "Commercial Property", "Motor Vehicle", "Public Liability"])

    # Intentional conflicting information: different max coverage amounts
    # This document says max residential coverage is $1.5M
    max_coverage = random.choice([1500000, 2000000, 2500000])

    content = f"""
UNDERWRITING GUIDELINES — {risk_category}
Version: {random.randint(1, 5)}.{random.randint(0, 9)}
Last Updated: {fake.date_between(start_date='-2y', end_date='today').strftime('%d %B %Y')}
Classification: INTERNAL — CONFIDENTIAL

1. RISK ASSESSMENT CRITERIA

1.1 Acceptable Risks
- {risk_category} policies for properties valued between $100,000 and ${max_coverage:,}
- Property age: less than 80 years (or with recent structural inspection)
- Claims history: maximum 2 claims in the last 5 years
- Location: all Australian states and territories

1.2 Declined Risks
- Properties in designated flood zones without mitigation
- Buildings with known asbestos (unless removal plan documented)
- Properties with more than 3 claims in 3 years
- Commercial properties with hazardous materials storage

1.3 Referred Risks (require senior underwriter approval)
- Properties valued above ${max_coverage:,}
- Heritage-listed buildings
- Properties in bushfire-prone areas (BAL rating FZ)
- Strata properties with known building defects

2. PRICING MATRIX

Base premium rates per $1,000 of coverage:
- Low risk (metro, new build, no claims): $1.20
- Medium risk (regional, 10-30yr old, 1 claim): $2.45
- High risk (rural, 30yr+, 2 claims): $4.80
- Very high risk (referred): Individual assessment required

Minimum premium: $350 per annum
Maximum discount: 25% (loyalty + no claims + multi-policy)

3. APPROVAL AUTHORITY

| Coverage Amount | Approval Level |
|---|---|
| Up to $500,000 | Underwriter |
| $500,001 — $1,000,000 | Senior Underwriter |
| $1,000,001 — ${max_coverage:,} | Underwriting Manager |
| Above ${max_coverage:,} | Chief Underwriter |

4. DOCUMENTATION REQUIREMENTS

For all new policies:
- Completed application form
- Proof of ownership or insurable interest
- Recent property valuation (within 12 months)
- Building inspection report (for properties over 40 years)
- Claims history declaration

Contact: Underwriting Team
Email: underwriting@raainsurance.com.au
Phone: 08 8202 {random.randint(1000, 9999)}
ABN: {generate_abn()}
"""

    return {
        "id": str(uuid4()),
        "filename": f"underwriting_guidelines_{risk_category.lower().replace(' ', '_')}_{doc_id:03d}.txt",
        "source_domain": "insurance",
        "file_type": "txt",
        "content": content.strip(),
        "metadata": {
            "document_type": "underwriting_guidelines",
            "risk_category": risk_category,
            "max_coverage": max_coverage,
        },
    }


# ─────────────────────────────────────────────
# Financial Services Domain Documents
# ─────────────────────────────────────────────


def generate_compliance_report(doc_id: int) -> dict:
    """Generate a synthetic APRA compliance report."""
    reporting_period = f"Q{random.randint(1, 4)} {random.randint(2024, 2025)}"
    entity = random.choice(["Adelaide Mutual Insurance", "Southern Cross Financial", "Pacific Re", "Coastal Underwriters"])
    abn = generate_abn()

    content = f"""
PRUDENTIAL COMPLIANCE REPORT
Australian Prudential Regulation Authority (APRA)

Reporting Entity: {entity}
ABN: {abn}
APRA Registration: INS-{random.randint(10000, 99999)}
Reporting Period: {reporting_period}
Submitted: {fake.date_between(start_date='-6m', end_date='today').strftime('%d/%m/%Y')}
Prepared by: {fake.name()} — Chief Risk Officer
Contact: {fake.email()}

1. CAPITAL ADEQUACY (CPS 110)

Prescribed Capital Amount (PCA): ${random.randint(50, 200)} million
Capital Base: ${random.randint(60, 300)} million
Capital Adequacy Ratio: {random.randint(150, 250)}%
Minimum requirement: 100%
Status: COMPLIANT

2. RISK MANAGEMENT (CPS 220)

Risk Management Framework: Reviewed {fake.date_between(start_date='-1y', end_date='today').strftime('%B %Y')}
Key risks identified:
- Cyber security threats (rating: {random.choice(['High', 'Medium', 'Low'])})
- Climate-related financial risks (rating: {random.choice(['High', 'Medium'])})
- Concentration risk in residential property portfolio (rating: {random.choice(['Medium', 'Low'])})

Board Risk Committee meetings held: {random.randint(4, 12)}
Risk appetite breaches: {random.randint(0, 3)}

3. INFORMATION SECURITY (CPS 234)

Information security incidents reported: {random.randint(0, 5)}
Critical vulnerabilities identified: {random.randint(0, 2)}
Penetration testing completed: {random.choice(['Yes', 'No', 'In Progress'])}
Third-party security assessments: {random.randint(1, 4)} completed

4. GOVERNANCE (CPS 510)

Board composition:
- Independent directors: {random.randint(3, 7)}
- Executive directors: {random.randint(1, 3)}
- Board meetings held: {random.randint(6, 12)}

Fit and proper assessments: All directors current
Conflict of interest declarations: Up to date

5. OUTSOURCING (CPS 231)

Material outsourcing arrangements: {random.randint(2, 8)}
Offshore arrangements: {random.randint(0, 3)}
All arrangements within risk appetite: {random.choice(['Yes', 'No — remediation plan in place'])}

6. DECLARATION

I, {fake.name()}, CEO of {entity}, declare that to the best of my knowledge,
the information contained in this report is accurate and complete.

Signed: [Digital signature]
Date: {fake.date_between(start_date='-1m', end_date='today').strftime('%d/%m/%Y')}

Medicare Number on file for CEO verification: {generate_medicare()}
"""

    return {
        "id": str(uuid4()),
        "filename": f"apra_compliance_{entity.lower().replace(' ', '_')}_{reporting_period.lower().replace(' ', '_')}_{doc_id:03d}.txt",
        "source_domain": "financial",
        "file_type": "txt",
        "content": content.strip(),
        "metadata": {
            "document_type": "compliance_report",
            "regulator": "APRA",
            "entity": entity,
            "period": reporting_period,
        },
    }


def generate_risk_assessment(doc_id: int) -> dict:
    """Generate a synthetic risk assessment as JSON."""
    categories = ["Operational", "Credit", "Market", "Liquidity", "Cyber", "Climate"]

    risks = []
    for i in range(random.randint(5, 12)):
        category = random.choice(categories)
        risks.append({
            "risk_id": f"RSK-{random.randint(1000, 9999)}",
            "category": category,
            "description": fake.sentence(nb_words=10),
            "likelihood": random.choice(["Rare", "Unlikely", "Possible", "Likely", "Almost Certain"]),
            "impact": random.choice(["Insignificant", "Minor", "Moderate", "Major", "Catastrophic"]),
            "risk_rating": random.choice(["Low", "Medium", "High", "Critical"]),
            "owner": fake.name(),  # Intentional PII
            "owner_email": fake.email(),  # Intentional PII
            "mitigation": fake.sentence(nb_words=8),
            "review_date": fake.date_between(start_date="-6m", end_date="+6m").isoformat(),
            "status": random.choice(["Open", "Mitigated", "Accepted", "Transferred"]),
        })

    return {
        "id": str(uuid4()),
        "filename": f"risk_assessment_{random.randint(2024, 2025)}_{doc_id:03d}.json",
        "source_domain": "financial",
        "file_type": "json",
        "content": {
            "assessment_date": fake.date_between(start_date="-3m", end_date="today").isoformat(),
            "assessor": fake.name(),
            "entity": "Southern Cross Financial Services",
            "abn": generate_abn(),
            "risks": risks,
            "summary": {
                "total_risks": len(risks),
                "critical": sum(1 for r in risks if r["risk_rating"] == "Critical"),
                "high": sum(1 for r in risks if r["risk_rating"] == "High"),
                "medium": sum(1 for r in risks if r["risk_rating"] == "Medium"),
                "low": sum(1 for r in risks if r["risk_rating"] == "Low"),
            },
        },
        "metadata": {
            "document_type": "risk_assessment",
            "year": random.randint(2024, 2025),
        },
    }


# ─────────────────────────────────────────────
# Government Domain Documents
# ─────────────────────────────────────────────


def generate_council_policy(doc_id: int) -> dict:
    """Generate a synthetic council policy document."""
    policy_areas = [
        "Community Grants Program",
        "Asset Management",
        "Procurement and Contracts",
        "Data Governance",
        "Workplace Health and Safety",
        "Environmental Sustainability",
        "Public Consultation",
        "Freedom of Information",
    ]
    policy_area = random.choice(policy_areas)
    council = random.choice(["City of Salisbury", "City of Adelaide", "City of Charles Sturt", "City of Marion"])

    # Intentional: some documents are stale (2019 dates)
    if random.random() < 0.15:
        approval_date = fake.date_between(start_date="-6y", end_date="-4y")
        review_note = "\n⚠️ NOTE: This policy has not been reviewed since its original approval date and may contain outdated information.\n"
    else:
        approval_date = fake.date_between(start_date="-2y", end_date="today")
        review_note = ""

    next_review = approval_date + timedelta(days=random.choice([365, 730, 1095]))

    content = f"""
{council.upper()}
COUNCIL POLICY

Policy Title: {policy_area}
Policy Number: CP-{random.randint(100, 999)}
Version: {random.randint(1, 4)}.{random.randint(0, 5)}
Approval Date: {approval_date.strftime('%d %B %Y')}
Next Review Date: {next_review.strftime('%d %B %Y')}
Responsible Officer: {fake.name()}, {random.choice(['Director Corporate Services', 'Director Community Services', 'Director Infrastructure', 'Manager Governance'])}
Contact: {fake.email()}
Phone: 08 8406 {random.randint(1000, 9999)}
{review_note}
1. PURPOSE

This policy establishes the framework for {policy_area.lower()} within {council}.
It ensures transparency, accountability, and consistency in how the Council
manages {policy_area.lower()} processes.

2. SCOPE

This policy applies to:
- All Council employees and contractors
- Elected Members (where applicable)
- Volunteers working on behalf of Council
- Third-party service providers engaged by Council

3. POLICY STATEMENT

3.1 {council} is committed to best-practice {policy_area.lower()} that delivers
value to our community and meets all legislative requirements.

3.2 All decisions under this policy must comply with:
- Local Government Act 1999 (SA)
- State Procurement Act 2004 (where applicable)
- Council's Code of Conduct for Employees
- Relevant Australian Standards

3.3 Financial delegations apply as per Council's Financial Delegations Register.
Expenditure above ${random.choice([10000, 25000, 50000, 100000]):,} requires
{random.choice(['Manager', 'Director', 'CEO', 'Council'])} approval.

4. RESPONSIBILITIES

| Role | Responsibility |
|---|---|
| Council | Approve policy and strategic direction |
| CEO | Overall implementation and compliance |
| Directors | Operational compliance within division |
| Managers | Day-to-day implementation |
| All Staff | Adhere to this policy |

5. RELATED DOCUMENTS

- Council Strategic Plan 2024-2028
- Annual Business Plan
- Risk Management Framework
- Code of Conduct for Council Employees
- Fraud and Corruption Prevention Policy

6. REVIEW

This policy will be reviewed every {random.choice([1, 2, 3])} year(s) or earlier
if required by legislative changes.

Document Owner: {fake.name()}
ABN: {generate_abn()}
"""

    return {
        "id": str(uuid4()),
        "filename": f"council_policy_{policy_area.lower().replace(' ', '_')}_{council.lower().replace(' ', '_').replace('city_of_', '')}_{doc_id:03d}.txt",
        "source_domain": "government",
        "file_type": "txt",
        "content": content.strip(),
        "metadata": {
            "document_type": "council_policy",
            "policy_area": policy_area,
            "council": council,
            "approval_date": approval_date.isoformat(),
            "is_stale": approval_date.year < 2022,
        },
    }


def generate_procurement_record(doc_id: int) -> dict:
    """Generate synthetic procurement records as CSV."""
    num_records = random.randint(10, 30)
    records = []

    vendors = [
        "SA Power Networks", "Veolia Environmental", "Downer Group",
        "Fulton Hogan", "BMD Group", "McConnell Dowell",
        "Cardno (now Stantec)", "GHD", "AECOM", "Jacobs",
    ]

    for i in range(num_records):
        award_date = fake.date_between(start_date="-2y", end_date="today")
        value = round(random.uniform(5000, 2000000), 2)

        record = {
            "contract_id": f"CON-{random.randint(10000, 99999)}",
            "vendor": random.choice(vendors),
            "vendor_abn": generate_abn(),  # Intentional: ABN is not PII but is sensitive business data
            "description": fake.sentence(nb_words=8),
            "category": random.choice(["Infrastructure", "IT Services", "Professional Services", "Maintenance", "Waste Management"]),
            "contract_value": value,
            "award_date": award_date.strftime("%d/%m/%Y"),
            "end_date": (award_date + timedelta(days=random.randint(90, 1095))).strftime("%Y-%m-%d"),  # Intentional format inconsistency
            "procurement_method": random.choice(["Open Tender", "Select Tender", "Direct Negotiation", "Panel Contract"]),
            "approved_by": fake.name(),
        }

        # Intentional: some records have missing contract values
        if random.random() < 0.08:
            record["contract_value"] = ""

        records.append(record)

    return {
        "id": str(uuid4()),
        "filename": f"procurement_register_{random.randint(2023, 2025)}_{doc_id:03d}.csv",
        "source_domain": "government",
        "file_type": "csv",
        "content": records,
        "metadata": {
            "document_type": "procurement_register",
            "total_records": len(records),
        },
    }


# ─────────────────────────────────────────────
# Enterprise Domain Documents
# ─────────────────────────────────────────────


def generate_hr_policy(doc_id: int) -> dict:
    """Generate a synthetic HR policy document."""
    policies = [
        ("Remote Work Policy", "remote_work"),
        ("Code of Conduct", "code_of_conduct"),
        ("Leave and Absence Management", "leave_management"),
        ("Performance Review Process", "performance_review"),
        ("Anti-Discrimination and Harassment", "anti_discrimination"),
        ("Onboarding Procedure", "onboarding"),
    ]
    policy_name, policy_slug = random.choice(policies)
    company = random.choice(["Nexus Technologies", "AusTech Solutions", "Meridian Data Services"])

    content = f"""
{company}
HUMAN RESOURCES POLICY

Policy: {policy_name}
Document ID: HR-{random.randint(100, 999)}
Effective Date: {fake.date_between(start_date='-2y', end_date='today').strftime('%d %B %Y')}
Version: {random.randint(1, 3)}.{random.randint(0, 5)}
Owner: {fake.name()}, Head of People & Culture
Email: {fake.email()}
Classification: Internal Use Only

1. OVERVIEW

{company} is committed to maintaining a workplace that supports employee
wellbeing, productivity, and professional growth. This {policy_name} outlines
the standards and expectations for all employees.

2. APPLICATION

This policy applies to all employees of {company}, including:
- Full-time and part-time permanent employees
- Fixed-term contract employees
- Casual employees (where applicable)
- Contractors and consultants (where specified)

3. KEY PROVISIONS

3.1 All employees must complete the relevant acknowledgement form within
14 days of this policy's effective date.

3.2 Managers are responsible for ensuring their teams understand and comply
with this policy. Non-compliance may result in disciplinary action up to
and including termination.

3.3 Any questions regarding this policy should be directed to the
People & Culture team at hr@{company.lower().replace(' ', '')}.com.au

4. RELATED POLICIES

- Employee Handbook v{random.randint(1, 5)}.0
- Workplace Health & Safety Policy
- Privacy and Data Protection Policy
- Grievance Resolution Procedure

5. REVIEW HISTORY

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | {fake.date_between(start_date='-3y', end_date='-2y').strftime('%d/%m/%Y')} | {fake.name()} | Initial release |
| 2.0 | {fake.date_between(start_date='-1y', end_date='today').strftime('%d/%m/%Y')} | {fake.name()} | Annual review update |

ABN: {generate_abn()}
"""

    return {
        "id": str(uuid4()),
        "filename": f"hr_policy_{policy_slug}_{company.lower().replace(' ', '_')}_{doc_id:03d}.txt",
        "source_domain": "enterprise",
        "file_type": "txt",
        "content": content.strip(),
        "metadata": {
            "document_type": "hr_policy",
            "policy_name": policy_name,
            "company": company,
        },
    }


def generate_it_security_doc(doc_id: int) -> dict:
    """Generate a synthetic IT security assessment document."""
    company = random.choice(["Nexus Technologies", "AusTech Solutions", "Meridian Data Services"])
    assessment_date = fake.date_between(start_date="-6m", end_date="today")

    findings = []
    for i in range(random.randint(4, 10)):
        findings.append({
            "finding_id": f"SEC-{random.randint(1000, 9999)}",
            "severity": random.choice(["Critical", "High", "Medium", "Low", "Informational"]),
            "title": random.choice([
                "Unpatched production servers",
                "Weak password policy enforcement",
                "Missing MFA on admin accounts",
                "Excessive IAM permissions",
                "Unencrypted data at rest",
                "Missing WAF configuration",
                "Outdated SSL certificates",
                "Insufficient logging and monitoring",
                "Open S3 bucket detected",
                "No network segmentation between environments",
            ]),
            "description": fake.paragraph(nb_sentences=2),
            "affected_system": random.choice(["AWS Production", "Azure DevTest", "Corporate Network", "SaaS Applications", "Database Tier"]),
            "remediation": fake.sentence(nb_words=10),
            "status": random.choice(["Open", "In Progress", "Remediated", "Accepted Risk"]),
            "assigned_to": fake.name(),
            "assigned_email": fake.email(),  # Intentional PII
        })

    return {
        "id": str(uuid4()),
        "filename": f"security_assessment_{company.lower().replace(' ', '_')}_{assessment_date.strftime('%Y%m')}_{doc_id:03d}.json",
        "source_domain": "enterprise",
        "file_type": "json",
        "content": {
            "assessment_type": "Annual Security Review",
            "company": company,
            "abn": generate_abn(),
            "assessment_date": assessment_date.isoformat(),
            "assessor": f"{fake.name()} — {random.choice(['CyberCX', 'Tesserent', 'Deloitte Cyber', 'PwC Digital Trust'])}",
            "overall_rating": random.choice(["Satisfactory", "Needs Improvement", "Unsatisfactory"]),
            "findings": findings,
            "summary": {
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f["severity"] == "Critical"),
                "high": sum(1 for f in findings if f["severity"] == "High"),
                "medium": sum(1 for f in findings if f["severity"] == "Medium"),
                "low": sum(1 for f in findings if f["severity"] == "Low"),
            },
            "next_review": (assessment_date + timedelta(days=365)).isoformat(),
        },
        "metadata": {
            "document_type": "security_assessment",
            "company": company,
        },
    }


# ─────────────────────────────────────────────
# Intentional Data Quality Issues
# ─────────────────────────────────────────────


def generate_malformed_csv(doc_id: int) -> dict:
    """Generate a CSV with intentional structural problems."""
    # Misaligned columns, extra commas, inconsistent quoting
    raw_content = """claim_id,policy_number,claimant,amount,status
CLM-999001,RAA-100001,John Smith,15000.00,Approved
CLM-999002,RAA-100002,"Jane O'Brien, Jr.",22500.00,Under Assessment
CLM-999003,RAA-100003,Bob Wilson,amount_not_available,Pending
CLM-999004,,Michael Chen,18000.00,Approved,extra_field_here
CLM-999005,RAA-100005,Sarah   Johnson,,Declined
,RAA-100006,David Lee,9500.00,Open
CLM-999007,RAA-100007,"Lisa ""Liz"" Taylor",31000.00,Paid
CLM-999008,RAA-100008,Test User,0,
CLM-999009,RAA-100009,
CLM-999010,RAA-100010,Emma Davis,45000.00,Approved"""

    return {
        "id": str(uuid4()),
        "filename": f"claims_export_malformed_{doc_id:03d}.csv",
        "source_domain": "insurance",
        "file_type": "csv_raw",  # Special type — raw string, not structured
        "content": raw_content.strip(),
        "metadata": {
            "document_type": "malformed_data",
            "issues": ["misaligned_columns", "missing_values", "extra_fields", "inconsistent_quoting"],
        },
    }


def generate_conflicting_document(doc_id: int) -> dict:
    """Generate a document that contradicts information in underwriting guidelines.

    The underwriting guidelines say max residential coverage is $1.5M-$2.5M.
    This document says it's $3M — creating a conflict the quality agent should detect.
    """
    content = f"""
RAA INSURANCE — PRODUCT UPDATE BULLETIN

Bulletin No: PUB-{random.randint(100, 999)}
Date: {fake.date_between(start_date='-6m', end_date='today').strftime('%d %B %Y')}
Distribution: All Underwriters, All Brokers

SUBJECT: Updated Coverage Limits — Residential Property

Effective immediately, the following changes apply to residential property coverage:

1. Maximum sum insured for residential property: $3,000,000
   (Previously: $1,500,000)

2. Excess structure unchanged

3. All policies above $2,000,000 require:
   - Independent property valuation (within 6 months)
   - Building inspection report
   - Senior Underwriter approval

Please update your reference materials accordingly.

IMPORTANT: This bulletin supersedes Section 1.1 of the Underwriting Guidelines
for Residential Property. A revised guideline document will be issued within
30 days.

Issued by: {fake.name()}
Title: Chief Underwriter
Email: {fake.email()}
Phone: 08 8202 {random.randint(1000, 9999)}
"""

    return {
        "id": str(uuid4()),
        "filename": f"product_update_bulletin_{doc_id:03d}.txt",
        "source_domain": "insurance",
        "file_type": "txt",
        "content": content.strip(),
        "metadata": {
            "document_type": "product_bulletin",
            "conflicts_with": "underwriting_guidelines",
            "new_max_coverage": 3000000,
        },
    }


# ─────────────────────────────────────────────
# Document Writer
# ─────────────────────────────────────────────


def write_document(doc: dict, output_dir: Path) -> Path:
    """Write a generated document to disk."""
    domain_dir = output_dir / doc["source_domain"]
    domain_dir.mkdir(parents=True, exist_ok=True)

    filepath = domain_dir / doc["filename"]

    if doc["file_type"] == "csv" and isinstance(doc["content"], list):
        # Write structured CSV
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if doc["content"]:
                writer = csv.DictWriter(f, fieldnames=doc["content"][0].keys())
                writer.writeheader()
                writer.writerows(doc["content"])

    elif doc["file_type"] == "json" and isinstance(doc["content"], dict):
        # Write JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(doc["content"], f, indent=2, default=str)

    elif doc["file_type"] == "csv_raw":
        # Write raw malformed CSV (intentionally broken)
        with open(filepath.with_suffix(".csv"), "w", encoding="utf-8") as f:
            f.write(doc["content"])
        filepath = filepath.with_suffix(".csv")

    else:
        # Write text document
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(doc["content"])

    # Write metadata sidecar
    meta_path = filepath.with_suffix(filepath.suffix + ".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        meta = {
            "id": doc["id"],
            "filename": doc["filename"],
            "source_domain": doc["source_domain"],
            "file_type": doc["file_type"],
            "metadata": doc["metadata"],
            "generated_at": datetime.now().isoformat(),
        }
        json.dump(meta, f, indent=2, default=str)

    return filepath


# ─────────────────────────────────────────────
# Main Generator
# ─────────────────────────────────────────────


# Document generation functions mapped by domain
GENERATORS = {
    "insurance": [
        (generate_insurance_policy, 8),
        (generate_claims_report, 4),
        (generate_underwriting_guidelines, 3),
        (generate_conflicting_document, 2),
        (generate_malformed_csv, 2),
    ],
    "financial": [
        (generate_compliance_report, 5),
        (generate_risk_assessment, 5),
    ],
    "government": [
        (generate_council_policy, 8),
        (generate_procurement_record, 4),
    ],
    "enterprise": [
        (generate_hr_policy, 6),
        (generate_it_security_doc, 5),
    ],
}


def generate_all_documents(output_dir: Path) -> list[dict]:
    """Generate all synthetic documents across all domains."""
    documents = []
    doc_id = 1

    print("🏗️  Generating synthetic enterprise documents...\n")

    for domain, generators in GENERATORS.items():
        domain_count = 0
        for generator_fn, count in generators:
            for _ in range(count):
                doc = generator_fn(doc_id)
                filepath = write_document(doc, output_dir)
                documents.append(doc)
                domain_count += 1
                doc_id += 1

        print(f"  📁 {domain:<15} {domain_count:>3} documents")

    # Generate one exact duplicate (same content, different filename)
    if documents:
        duplicate = documents[0].copy()
        duplicate["id"] = str(uuid4())
        duplicate["filename"] = "DUPLICATE_" + duplicate["filename"]
        filepath = write_document(duplicate, output_dir)
        documents.append(duplicate)

    print(f"\n✅ Total: {len(documents)} documents generated")
    print(f"📂 Output: {output_dir.resolve()}")

    # Print data quality summary
    pii_types = ["names", "emails", "phone numbers", "ABNs", "Medicare numbers"]
    print(f"\n🔍 Intentional data quality issues included:")
    print(f"   • PII leakage: {', '.join(pii_types)}")
    print(f"   • 1 exact duplicate document")
    print(f"   • 1 duplicate claim row (in CSV)")
    print(f"   • 2 malformed CSV files")
    print(f"   • 2 conflicting documents (coverage limits)")
    print(f"   • ~15% stale government policies (pre-2022)")
    print(f"   • Mixed date formats (DD/MM/YYYY vs MM-DD-YYYY vs YYYY-MM-DD)")
    print(f"   • Missing field values (~5-8% of rows)")

    return documents


def generate_manifest(documents: list[dict], output_dir: Path) -> None:
    """Write a manifest file listing all generated documents."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "total_documents": len(documents),
        "by_domain": {},
        "by_type": {},
        "documents": [],
    }

    for doc in documents:
        domain = doc["source_domain"]
        ftype = doc["file_type"]
        manifest["by_domain"][domain] = manifest["by_domain"].get(domain, 0) + 1
        manifest["by_type"][ftype] = manifest["by_type"].get(ftype, 0) + 1
        manifest["documents"].append({
            "id": doc["id"],
            "filename": doc["filename"],
            "source_domain": doc["source_domain"],
            "file_type": doc["file_type"],
        })

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"📋 Manifest: {manifest_path.resolve()}")


def main() -> None:
    """Generate synthetic documents and save to output directory."""
    parser = argparse.ArgumentParser(description="Generate synthetic test documents for RIPPAA AI Data Platform")
    parser.add_argument("--output-dir", type=str, default="data/synthetic", help="Output directory for generated documents")
    args = parser.parse_args()

    output_path = Path(args.output_dir)

    # Clean previous run
    if output_path.exists():
        import shutil
        shutil.rmtree(output_path)

    output_path.mkdir(parents=True, exist_ok=True)

    documents = generate_all_documents(output_path)
    generate_manifest(documents, output_path)

    print("\n🎉 Done! Synthetic data is ready for pipeline ingestion.")


if __name__ == "__main__":
    main()
