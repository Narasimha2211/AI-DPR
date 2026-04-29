# ============================================
# Table Extractor for DPR Financial Data
# Extracts budget tables, BOQ, cost estimates
# ============================================

import re
from typing import Optional

import pandas as pd
from loguru import logger


class TableExtractor:
    """
    Specialized extractor for DPR tables:
    - Budget/Cost tables
    - Bill of Quantities (BOQ)
    - Project timeline tables
    - Resource allocation tables
    """

    # Common DPR table headers
    BUDGET_KEYWORDS = [
        "cost", "budget", "amount", "estimate", "expenditure",
        "allocation", "rs", "inr", "crore", "lakh", "total"
    ]

    TIMELINE_KEYWORDS = [
        "milestone", "phase", "duration", "start", "end",
        "month", "year", "quarter", "schedule", "timeline"
    ]

    BOQ_KEYWORDS = [
        "item", "quantity", "unit", "rate", "amount",
        "description", "sl", "no", "boq"
    ]

    def __init__(self):
        logger.info("TableExtractor initialized")

    def extract_tables_from_text(self, tables_data: list) -> dict:
        """
        Process extracted table data and classify them.

        Args:
            tables_data: List of table dicts from pdf_extractor

        Returns:
            Classified tables with analysis
        """
        result = {
            "budget_tables": [],
            "timeline_tables": [],
            "boq_tables": [],
            "other_tables": [],
            "total_tables": len(tables_data),
            "summary": {}
        }

        for table_info in tables_data:
            data = table_info.get("data", [])
            if not data or len(data) < 2:
                continue

            # Clean table data
            cleaned = self._clean_table(data)
            if not cleaned:
                continue

            # Classify table
            classification = self._classify_table(cleaned)

            table_entry = {
                "page_number": table_info.get("page_number", 0),
                "data": [{"cells": row} for row in cleaned],
                "rows": len(cleaned),
                "cols": len(cleaned[0]) if cleaned else 0,
                "headers": cleaned[0] if cleaned else [],
                "classification": classification
            }

            if classification == "budget":
                table_entry["financial_summary"] = self._analyze_budget_table(cleaned)
                result["budget_tables"].append(table_entry)
            elif classification == "timeline":
                table_entry["timeline_summary"] = self._analyze_timeline_table(cleaned)
                result["timeline_tables"].append(table_entry)
            elif classification == "boq":
                table_entry["boq_summary"] = self._analyze_boq_table(cleaned)
                result["boq_tables"].append(table_entry)
            else:
                result["other_tables"].append(table_entry)

        # Summary
        result["summary"] = {
            "budget_tables_found": len(result["budget_tables"]),
            "timeline_tables_found": len(result["timeline_tables"]),
            "boq_tables_found": len(result["boq_tables"]),
            "other_tables_found": len(result["other_tables"]),
            "total_cost_extracted": self._get_total_cost(result["budget_tables"])
        }

        logger.info(
            f"Table extraction complete: {result['summary']}"
        )
        return result

    def _clean_table(self, data: list) -> list:
        """Clean raw table data."""
        cleaned = []
        for row in data:
            if row is None:
                continue
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    cleaned_row.append(str(cell).strip())
            if any(cell for cell in cleaned_row):
                cleaned.append(cleaned_row)
        return cleaned

    def _classify_table(self, data: list) -> str:
        """Classify table type based on headers and content."""
        if not data:
            return "other"

        # Combine headers and first few rows for classification
        check_text = " ".join(
            " ".join(row) for row in data[:3]
        ).lower()

        budget_score = sum(1 for kw in self.BUDGET_KEYWORDS if kw in check_text)
        timeline_score = sum(1 for kw in self.TIMELINE_KEYWORDS if kw in check_text)
        boq_score = sum(1 for kw in self.BOQ_KEYWORDS if kw in check_text)

        scores = {
            "budget": budget_score,
            "timeline": timeline_score,
            "boq": boq_score
        }

        max_score = max(scores.values())
        if max_score >= 2:
            return max(scores, key=lambda k: scores[k])
        return "other"

    def _analyze_budget_table(self, data: list) -> dict:
        """Analyze a budget table to extract financial information."""
        analysis = {
            "total_amount": 0,
            "line_items": [],
            "currency_unit": "unknown"
        }

        for row in data[1:]:  # Skip header
            amounts = []
            description = ""
            for i, cell in enumerate(row):
                # Try to find monetary values
                num = self._extract_number(cell)
                if num is not None:
                    amounts.append(num)
                elif cell and not cell.replace(" ", "").isdigit():
                    description = cell

            if amounts:
                analysis["line_items"].append({
                    "description": description,
                    "amount": max(amounts)  # Usually the rightmost/largest is the total
                })

        if analysis["line_items"]:
            analysis["total_amount"] = sum(item["amount"] for item in analysis["line_items"])

        return analysis

    def _analyze_timeline_table(self, data: list) -> dict:
        """Analyze a timeline table."""
        analysis = {
            "milestones": [],
            "total_duration": ""
        }

        for row in data[1:]:
            milestone = {
                "phase": row[0] if row else "",
                "details": " | ".join(row[1:]) if len(row) > 1 else ""
            }
            analysis["milestones"].append(milestone)

        return analysis

    def _analyze_boq_table(self, data: list) -> dict:
        """Analyze a Bill of Quantities table."""
        analysis = {
            "items": [],
            "total_items": 0,
            "total_amount": 0
        }

        for row in data[1:]:
            item = {
                "description": row[1] if len(row) > 1 else row[0] if row else "",
                "quantity": self._extract_number(row[2]) if len(row) > 2 else None,
                "rate": self._extract_number(row[3]) if len(row) > 3 else None,
                "amount": self._extract_number(row[-1]) if row else None
            }
            analysis["items"].append(item)

        analysis["total_items"] = len(analysis["items"])
        analysis["total_amount"] = sum(
            item["amount"] or 0 for item in analysis["items"]
        )

        return analysis

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract numeric value from a string."""
        if not text:
            return None
        cleaned = re.sub(r"[^\d.,]", "", str(text))
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _get_total_cost(self, budget_tables: list) -> float:
        """Get total cost across all budget tables."""
        total = 0
        for table in budget_tables:
            summary = table.get("financial_summary", {})
            total += summary.get("total_amount", 0)
        return total

    def tables_to_dataframe(self, table_data: list) -> pd.DataFrame:
        """Convert table data to pandas DataFrame."""
        if not table_data or len(table_data) < 2:
            return pd.DataFrame()

        headers = table_data[0]
        rows = table_data[1:]

        # Clean headers
        headers = [h if h else f"Column_{i}" for i, h in enumerate(headers)]

        return pd.DataFrame(rows, columns=headers)
