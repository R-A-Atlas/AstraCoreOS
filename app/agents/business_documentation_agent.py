from __future__ import annotations

import re

from app.agent_packets import ContextPacket


class BusinessDocumentationAgent:
    name = "business_documentation_agent"

    def gather(self, directive: str) -> ContextPacket:
        text = (directive or "").strip()
        lowered = text.lower()
        document_type = self._document_type(lowered)
        business = self._business_topic(lowered)
        sections = self._sections_for(document_type)
        warnings = self._warnings(lowered)
        confidence = 0.88 if business != "general business" else 0.68

        data = {
            "document_type": document_type,
            "business": business,
            "format": self._format(lowered),
            "recommended_sections": sections,
            "operating_assumptions": self._assumptions_for(business, document_type),
            "quality_bar": [
                "clear enough for a real operator to use",
                "specific next steps instead of generic filler",
                "risks and missing details called out explicitly",
            ],
        }

        return ContextPacket(
            agent=self.name,
            task="business_documentation",
            status="ready",
            confidence=confidence,
            sources=[
                "local:business_plan_framework_v1",
                "local:small_business_operations_checklist_v1",
                "local:proposal_and_sop_templates_v1",
            ],
            data=data,
            summary=(
                f"Prepared a {document_type.replace('_', ' ')} framework for "
                f"{business} with {len(sections)} recommended sections."
            ),
            warnings=warnings,
        )

    @staticmethod
    def _document_type(text: str) -> str:
        if re.search(r"\bsop\b|standard operating|checklist|process|procedure", text):
            return "sop"
        if re.search(r"\bproposal\b|quote|client pitch|bid\b", text):
            return "proposal"
        if re.search(r"\bfinance report\b|financial report|budget|forecast|projection", text):
            return "finance_report"
        if re.search(r"\breport\b|audit|brief|summary", text):
            return "one_page_report"
        return "business_plan"

    @staticmethod
    def _business_topic(text: str) -> str:
        known = [
            ("mobile detailing", ["mobile detailing", "detailing business", "car detailing"]),
            ("cleaning business", ["cleaning business", "house cleaning", "commercial cleaning"]),
            ("local web design service", ["web design", "website service", "web agency"]),
            ("small bakery", ["bakery", "bake shop", "baking business"]),
            ("landscaping business", ["landscaping", "lawn care"]),
            ("real estate service", ["real estate", "property management"]),
            ("bookkeeping service", ["bookkeeping", "accounting service"]),
        ]
        for label, needles in known:
            if any(needle in text for needle in needles):
                return label
        match = re.search(r"for (?:a |an |the )?([a-z0-9][a-z0-9\s&-]{3,60}?)(?: business| company| service| startup|\.|$)", text)
        if match:
            return match.group(1).strip()
        return "general business"

    @staticmethod
    def _format(text: str) -> str:
        if "pdf" in text:
            return "pdf"
        if "word" in text or "docx" in text or "document" in text or "file" in text:
            return "docx"
        return "chat"

    @staticmethod
    def _sections_for(document_type: str) -> list[str]:
        sections = {
            "business_plan": [
                "Executive Summary",
                "Offer",
                "Target Customer",
                "Startup Needs",
                "Pricing Model",
                "Marketing Plan",
                "Operations",
                "30-Day Plan",
                "Risks",
                "Bottom Line",
            ],
            "proposal": [
                "Client Problem",
                "Recommended Solution",
                "Scope of Work",
                "Timeline",
                "Investment",
                "Success Metrics",
                "Next Step",
            ],
            "sop": [
                "Purpose",
                "Required Materials",
                "Step-by-Step Procedure",
                "Quality Check",
                "Common Failure Points",
                "Owner",
            ],
            "finance_report": [
                "Snapshot",
                "Revenue Drivers",
                "Cost Structure",
                "Cash Needs",
                "Risks",
                "Next 30 Days",
            ],
            "one_page_report": [
                "Context",
                "Key Findings",
                "Operational Impact",
                "Risks",
                "Recommended Next Steps",
            ],
        }
        return sections[document_type]

    @staticmethod
    def _assumptions_for(business: str, document_type: str) -> list[str]:
        if business == "mobile detailing":
            return [
                "local service business with low fixed overhead",
                "primary growth channels are Google Business Profile, referrals, and before/after content",
                "pricing should start simple with three packages",
            ]
        if business == "cleaning business":
            return [
                "repeat customers and scheduling reliability matter more than one-off volume",
                "quality control checklists reduce callbacks",
                "insurance and clear scope boundaries matter before commercial work",
            ]
        if business == "local web design service":
            return [
                "small business clients need clear scope, timeline, and ownership terms",
                "recurring maintenance can stabilize revenue",
                "proposal should avoid vague deliverables",
            ]
        if business == "small bakery":
            return [
                "cash flow depends on ingredient cost control and predictable demand",
                "waste and labor scheduling are core risks",
                "local repeat traffic and catering can improve margin stability",
            ]
        return [
            f"{document_type.replace('_', ' ')} should stay practical and specific",
            "missing business details should be called out instead of invented",
        ]

    @staticmethod
    def _warnings(text: str) -> list[str]:
        warnings = []
        if not re.search(r"\b(word|docx|pdf|document|file|report|plan|proposal|sop|checklist)\b", text):
            warnings.append("No output format was specified, so the agent will default to a chat-ready brief.")
        if "legal" in text or "contract" in text:
            warnings.append("Legal documents should be reviewed by a licensed attorney before use.")
        return warnings
