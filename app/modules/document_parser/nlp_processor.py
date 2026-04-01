# ============================================
# NLP Processor for DPR Content Analysis
# Extracts sections, entities, and key information
# ============================================

import re
from typing import Optional

from loguru import logger

from config.settings import settings


class NLPProcessor:
    """
    NLP engine for DPR document analysis.
    - Section identification & segmentation
    - Named Entity Recognition (NER)
    - Key phrase extraction
    - Financial figure extraction
    - Date/timeline extraction
    """

    # Common DPR section header patterns
    SECTION_PATTERNS = {
        "executive_summary": [
            r"(?i)executive\s+summary",
            r"(?i)abstract",
            r"(?i)overview\s+of\s+the\s+project"
        ],
        "project_background": [
            r"(?i)project\s+background",
            r"(?i)background\s+and\s+justification",
            r"(?i)project\s+context",
            r"(?i)need\s+for\s+the\s+project",
            r"(?i)introduction"
        ],
        "objectives": [
            r"(?i)project\s+objectives?",
            r"(?i)aims?\s+and\s+objectives?",
            r"(?i)goals?\s+of\s+the\s+project"
        ],
        "scope_of_work": [
            r"(?i)scope\s+of\s+work",
            r"(?i)project\s+scope",
            r"(?i)work\s+scope",
            r"(?i)scope\s+and\s+deliverables"
        ],
        "technical_feasibility": [
            r"(?i)technical\s+feasibility",
            r"(?i)technical\s+analysis",
            r"(?i)engineering\s+design",
            r"(?i)technical\s+details",
            r"(?i)technology\s+assessment"
        ],
        "financial_analysis": [
            r"(?i)financial\s+analysis",
            r"(?i)economic\s+analysis",
            r"(?i)financial\s+feasibility",
            r"(?i)cost\s+benefit\s+analysis",
            r"(?i)financial\s+viability"
        ],
        "cost_estimates": [
            r"(?i)cost\s+estimates?",
            r"(?i)project\s+cost",
            r"(?i)estimated\s+cost",
            r"(?i)budget\s+estimate",
            r"(?i)bill\s+of\s+quantities",
            r"(?i)boq"
        ],
        "implementation_schedule": [
            r"(?i)implementation\s+schedule",
            r"(?i)project\s+timeline",
            r"(?i)work\s+schedule",
            r"(?i)project\s+schedule",
            r"(?i)milestones?"
        ],
        "institutional_framework": [
            r"(?i)institutional\s+framework",
            r"(?i)organizational?\s+structure",
            r"(?i)project\s+management",
            r"(?i)implementation\s+arrangement"
        ],
        "environmental_impact": [
            r"(?i)environment(al)?\s+(and\s+social\s+)?impact",
            r"(?i)eia",
            r"(?i)environmental?\s+assessment",
            r"(?i)environmental?\s+clearance",
            r"(?i)social\s+impact"
        ],
        "risk_assessment": [
            r"(?i)risk\s+assessment",
            r"(?i)risk\s+analysis",
            r"(?i)risk\s+mitigation",
            r"(?i)risk\s+management",
            r"(?i)risk\s+register"
        ],
        "monitoring_evaluation": [
            r"(?i)monitoring\s+(and|&)\s+evaluation",
            r"(?i)m\s*&\s*e\s+framework",
            r"(?i)project\s+monitoring",
            r"(?i)performance\s+indicators"
        ],
        "sustainability": [
            r"(?i)sustainability\s+plan",
            r"(?i)operation\s+and\s+maintenance",
            r"(?i)o\s*&\s*m\s+plan",
            r"(?i)long[\s-]?term\s+sustainability"
        ],
        "annexures": [
            r"(?i)annexure",
            r"(?i)appendix",
            r"(?i)supporting\s+documents?",
            r"(?i)attachments?"
        ]
    }

    # Indian currency patterns
    CURRENCY_PATTERNS = [
        r"(?i)(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d{1,2})?\s*(?:crore|cr|lakh|lac|lakhs|crores?)?",
        r"(?i)[\d,]+(?:\.\d{1,2})?\s*(?:crore|cr|lakh|lac|lakhs|crores?)",
        r"(?i)(?:rupees?)\s*[\d,]+(?:\.\d{1,2})?",
    ]

    def __init__(self):
        self._spacy_model = None
        logger.info("NLPProcessor initialized")

    def _load_spacy(self):
        """Lazy-load spaCy model."""
        if self._spacy_model is None:
            try:
                import spacy
                self._spacy_model = spacy.load(settings.SPACY_MODEL)
                logger.info(f"spaCy model loaded: {settings.SPACY_MODEL}")
            except OSError:
                logger.warning(f"spaCy model '{settings.SPACY_MODEL}' not found. Downloading...")
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", settings.SPACY_MODEL])
                import spacy
                self._spacy_model = spacy.load(settings.SPACY_MODEL)
        return self._spacy_model

    def identify_sections(self, text: str) -> dict:
        """
        Identify and segment DPR sections from the full text.

        Returns:
            dict mapping section_name -> {start_pos, end_pos, text, word_count, found}
        """
        sections = {}
        text_lines = text.split("\n")

        # Find section headers and their positions
        section_positions = []
        for line_num, line in enumerate(text_lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            for section_name, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line_clean):
                        section_positions.append({
                            "section_name": section_name,
                            "line_number": line_num,
                            "header_text": line_clean
                        })
                        break

        # Sort by line number
        section_positions.sort(key=lambda x: x["line_number"])

        # Extract text between sections
        for i, sec in enumerate(section_positions):
            start_line = sec["line_number"]
            end_line = (
                section_positions[i + 1]["line_number"]
                if i + 1 < len(section_positions)
                else len(text_lines)
            )

            section_text = "\n".join(text_lines[start_line:end_line]).strip()
            sections[sec["section_name"]] = {
                "header": sec["header_text"],
                "text": section_text,
                "start_line": start_line,
                "end_line": end_line,
                "word_count": len(section_text.split()),
                "char_count": len(section_text),
                "found": True
            }

        # Mark missing sections
        for section_name in self.SECTION_PATTERNS.keys():
            if section_name not in sections:
                sections[section_name] = {
                    "header": "",
                    "text": "",
                    "start_line": -1,
                    "end_line": -1,
                    "word_count": 0,
                    "char_count": 0,
                    "found": False
                }

        found_count = sum(1 for s in sections.values() if s["found"])
        logger.info(f"Identified {found_count}/{len(self.SECTION_PATTERNS)} DPR sections")

        return sections

    def extract_entities(self, text: str) -> dict:
        """
        Extract named entities using spaCy NER (if available)
        or regex-based fallback.
        """
        entities = {
            "organizations": [],
            "locations": [],
            "dates": [],
            "monetary_values": [],
            "persons": [],
            "quantities": [],
            "other": []
        }

        try:
            nlp = self._load_spacy()
            doc = nlp(text[:100000])

            entity_label_map = {
                "ORG": "organizations",
                "GPE": "locations",
                "LOC": "locations",
                "DATE": "dates",
                "MONEY": "monetary_values",
                "PERSON": "persons",
                "QUANTITY": "quantities",
                "CARDINAL": "quantities"
            }

            seen = set()
            for ent in doc.ents:
                category = entity_label_map.get(ent.label_, "other")
                key = f"{category}:{ent.text.strip()}"
                if key not in seen and len(ent.text.strip()) > 1:
                    seen.add(key)
                    entities[category].append({
                        "text": ent.text.strip(),
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char
                    })
        except Exception:
            logger.warning("spaCy not available, using regex-based entity extraction")
            entities = self._regex_extract_entities(text)

        logger.info(
            f"Extracted entities: {sum(len(v) for v in entities.values())} total"
        )
        return entities

    def _regex_extract_entities(self, text: str) -> dict:
        """Regex-based entity extraction fallback when spaCy is unavailable."""
        entities = {
            "organizations": [], "locations": [], "dates": [],
            "monetary_values": [], "persons": [], "quantities": [], "other": []
        }

        # Organizations - common Indian govt bodies
        org_patterns = [
            r"(?:Ministry|Department|Directorate|Commission|Authority|Board|Corporation|Council|Committee|Institute|Agency|Bureau)"
            r"(?:\s+of)?(?:\s+[A-Z][a-zA-Z]+){1,5}",
            r"(?:NITI\s+Aayog|MDoNER|NEC|DONER|PWD|NHPC|BRO|NHAI|ISRO)",
            r"(?:Government|Govt\.?)\s+of\s+[A-Z][a-zA-Z ]+",
        ]
        for p in org_patterns:
            for m in re.finditer(p, text):
                entities["organizations"].append({"text": m.group().strip(), "label": "ORG", "start": m.start(), "end": m.end()})

        # Locations - Indian states and cities
        loc_words = [
            "Arunachal Pradesh", "Assam", "Manipur", "Meghalaya", "Mizoram",
            "Nagaland", "Sikkim", "Tripura", "New Delhi", "Delhi",
            "Guwahati", "Imphal", "Shillong", "Agartala", "Kohima",
            "Aizawl", "Itanagar", "Gangtok"
        ]
        for loc in loc_words:
            if loc.lower() in text.lower():
                entities["locations"].append({"text": loc, "label": "GPE", "start": 0, "end": 0})

        # Monetary values
        for pattern in self.CURRENCY_PATTERNS:
            for m in re.finditer(pattern, text):
                entities["monetary_values"].append({"text": m.group().strip(), "label": "MONEY", "start": m.start(), "end": m.end()})

        # Dates
        date_pats = [r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"]
        for p in date_pats:
            for m in re.finditer(p, text):
                entities["dates"].append({"text": m.group().strip(), "label": "DATE", "start": m.start(), "end": m.end()})

        # Deduplicate
        for cat in entities:
            seen = set()
            unique = []
            for e in entities[cat]:
                if e["text"] not in seen:
                    seen.add(e["text"])
                    unique.append(e)
            entities[cat] = unique

        return entities

    def extract_financial_figures(self, text: str) -> list:
        """
        Extract financial figures specifically (Indian currency format).
        Returns list of monetary values found in the DPR.
        """
        figures = []
        seen = set()

        for pattern in self.CURRENCY_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                value_text = match.group().strip()
                if value_text not in seen:
                    seen.add(value_text)
                    parsed = self._parse_indian_currency(value_text)
                    figures.append({
                        "raw_text": value_text,
                        "parsed_value": parsed["value"],
                        "unit": parsed["unit"],
                        "value_in_crores": parsed["value_in_crores"],
                        "position": match.start()
                    })

        # Sort by position in document
        figures.sort(key=lambda x: x["position"])
        logger.info(f"Extracted {len(figures)} financial figures")
        return figures

    def _parse_indian_currency(self, text: str) -> dict:
        """Parse Indian currency string to numeric value."""
        text_lower = text.lower().strip()

        # Remove currency symbols
        cleaned = re.sub(r"[₹$]|rs\.?|inr|rupees?", "", text_lower).strip()

        # Extract numeric part
        num_match = re.search(r"[\d,]+(?:\.\d+)?", cleaned)
        if not num_match:
            return {"value": 0, "unit": "unknown", "value_in_crores": 0}

        num_str = num_match.group().replace(",", "")
        if not num_str:
            return {"value": 0, "unit": "unknown", "value_in_crores": 0}

        try:
            value = float(num_str)
        except ValueError:
            return {"value": 0, "unit": "unknown", "value_in_crores": 0}

        # Determine unit
        if re.search(r"crore|cr", text_lower):
            unit = "crore"
            value_in_crores = value
        elif re.search(r"lakh|lac", text_lower):
            unit = "lakh"
            value_in_crores = value / 100
        else:
            unit = "rupees"
            value_in_crores = value / 10000000

        return {
            "value": value,
            "unit": unit,
            "value_in_crores": round(value_in_crores, 4)
        }

    def extract_dates_and_timelines(self, text: str) -> list:
        """Extract dates, durations, and timeline information."""
        date_patterns = [
            r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
            r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            r"(?:FY|fy)\s*\d{2,4}[-/]?\d{0,4}",
            r"\d{4}[-/]\d{2,4}",
            r"(?i)\d+\s+(?:months?|years?|weeks?|days?)",
        ]

        dates = []
        seen = set()
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                date_text = match.group().strip()
                if date_text not in seen:
                    seen.add(date_text)
                    dates.append({
                        "text": date_text,
                        "position": match.start(),
                        "type": self._classify_date_type(date_text)
                    })

        dates.sort(key=lambda x: x["position"])
        logger.info(f"Extracted {len(dates)} dates/timelines")
        return dates

    def _classify_date_type(self, text: str) -> str:
        """Classify a date string into type."""
        text_lower = text.lower()
        if re.search(r"fy|financial\s+year", text_lower):
            return "financial_year"
        elif re.search(r"months?|years?|weeks?|days?", text_lower):
            return "duration"
        else:
            return "date"

    def extract_key_phrases(self, text: str, top_n: int = 30) -> list:
        """Extract key phrases from the document."""
        try:
            nlp = self._load_spacy()
            doc = nlp(text[:50000])

            phrases = {}
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip().lower()
                if len(phrase.split()) >= 2 and len(phrase) > 5:
                    phrases[phrase] = phrases.get(phrase, 0) + 1

            sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
            return [{"phrase": p, "frequency": f} for p, f in sorted_phrases[:top_n]]
        except Exception:
            logger.warning("spaCy not available, using regex-based key phrase extraction")
            return self._regex_extract_phrases(text, top_n)

    def _regex_extract_phrases(self, text: str, top_n: int = 30) -> list:
        """Regex-based key phrase extraction fallback."""
        # Extract bigrams/trigrams from text
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stopwords = {'the','and','for','that','this','with','from','are','was','were','been',
                     'have','has','had','not','but','its','they','their','will','would','can',
                     'could','should','may','might','shall','also','into','over','such','than',
                     'other','which','these','those','being','all','any','each','every','both',
                     'more','most','some','about','between','through','during','before','after'}
        filtered = [w for w in words if w not in stopwords]

        phrases = {}
        for i in range(len(filtered) - 1):
            bigram = f"{filtered[i]} {filtered[i+1]}"
            phrases[bigram] = phrases.get(bigram, 0) + 1

        sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
        return [{"phrase": p, "frequency": f} for p, f in sorted_phrases[:top_n]]

    def compute_text_statistics(self, text: str) -> dict:
        """Compute basic text statistics for quality assessment."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]

        return {
            "total_words": len(words),
            "total_sentences": len(sentences),
            "total_paragraphs": len(paragraphs),
            "avg_words_per_sentence": round(len(words) / max(len(sentences), 1), 2),
            "avg_words_per_paragraph": round(len(words) / max(len(paragraphs), 1), 2),
            "unique_words": len(set(w.lower() for w in words)),
            "vocabulary_richness": round(len(set(w.lower() for w in words)) / max(len(words), 1), 4),
            "total_characters": len(text)
        }

    def analyze_document(self, text: str) -> dict:
        """
        Comprehensive NLP analysis of a DPR document.
        Combines all extraction methods.
        """
        logger.info("Starting comprehensive NLP analysis...")

        analysis = {
            "sections": self.identify_sections(text),
            "entities": self.extract_entities(text),
            "financial_figures": self.extract_financial_figures(text),
            "dates_timelines": self.extract_dates_and_timelines(text),
            "key_phrases": self.extract_key_phrases(text),
            "text_statistics": self.compute_text_statistics(text),
        }

        # Summary metrics
        found_sections = sum(1 for s in analysis["sections"].values() if s["found"])
        total_sections = len(analysis["sections"])

        analysis["summary"] = {
            "sections_found": found_sections,
            "sections_total": total_sections,
            "sections_completeness": round(found_sections / total_sections * 100, 2),
            "total_entities": sum(len(v) for v in analysis["entities"].values()),
            "total_financial_figures": len(analysis["financial_figures"]),
            "total_dates": len(analysis["dates_timelines"]),
        }

        logger.info(f"NLP analysis complete: {found_sections}/{total_sections} sections found")
        return analysis
