# ============================================
# Analysis Service - Document Processing
# Wrapper for NLP document analysis
# ============================================

import json
from typing import Optional
from loguru import logger
from app.modules.document_parser.nlp_processor import NLPProcessor
from app.modules.document_parser.pdf_extractor import PDFExtractor
from app.modules.document_parser.table_extractor import TableExtractor
from app.modules.document_parser.ocr_engine import OCREngine


async def analyze_document(file_path: str, state: Optional[str] = None) -> dict:
    """
    Analyze a document (PDF or DOCX) and extract insights.
    
    Args:
        file_path: Path to the document file
        state: Indian state name (optional)
    
    Returns:
        dict containing analysis results
    """
    try:
        logger.info(f"Starting analysis for: {file_path}")
        
        # Extract text from document
        pdf_extractor = PDFExtractor()
        extraction_result = pdf_extractor.extract_text(file_path)
        
        text: str = extraction_result.get("full_text", "")
        
        # Try OCR if text is too short
        if not text or len(text.strip()) < 100:
            logger.warning(f"Extracted text too short: {len(text)} chars")
            if extraction_result.get("needs_ocr"):
                ocr_engine = OCREngine()
                try:
                    ocr_result = ocr_engine.extract_text_from_pdf_images(file_path)
                    ocr_text = ocr_result.get("full_text", "") if isinstance(ocr_result, dict) else ""
                    text = ocr_text if ocr_text else text
                except Exception as e:
                    logger.warning(f"OCR fallback failed: {e}")
        
        # Ensure text is string
        if not isinstance(text, str):
            text = str(text) if text else ""
        
        # NLP Analysis
        nlp_processor = NLPProcessor()
        
        analysis = {
            "raw_text_length": len(text),
            "sections": nlp_processor.identify_sections(text),
            "entities": nlp_processor.extract_entities(text),
            "financial_figures": nlp_processor.extract_financial_figures(text),
            "dates_timelines": nlp_processor.extract_dates_and_timelines(text),
            "key_phrases": nlp_processor.extract_key_phrases(text),
            "text_statistics": nlp_processor.compute_text_statistics(text),
            "tables": extraction_result.get("tables", [])
        }
        
        logger.info(f"Analysis complete for: {file_path}")
        
        # CRITICAL: Deep conversion to ensure all values are primitives/JSON-compatible
        # Don't just call str() - actually convert to primitive types
        analysis = {
            "raw_text_length": int(analysis.get("raw_text_length", 0)),
            "sections": _convert_to_primitives(analysis.get("sections", {})),
            "entities": _convert_to_primitives(analysis.get("entities", {})),
            "financial_figures": _convert_to_primitives(analysis.get("financial_figures", [])),
            "dates_timelines": _convert_to_primitives(analysis.get("dates_timelines", [])),
            "key_phrases": _convert_to_primitives(analysis.get("key_phrases", [])),
            "text_statistics": _convert_to_primitives(analysis.get("text_statistics", {})),
            "tables": _convert_to_primitives(analysis.get("tables", []))
        }
        
        logger.info(f"Analysis fully converted for: {file_path}")
        return analysis
        
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise


def _convert_to_primitives(obj, depth=0):
    """
    Recursively convert all objects to primitive JSON types.
    Strips away ANY complex objects, keeping only str, int, float, bool, list, dict.
    """
    if depth > 20:  # Prevent infinite recursion
        return None
    
    # Primitives - pass through
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Handle iterables
    if isinstance(obj, (list, tuple)):
        return [_convert_to_primitives(item, depth+1) for item in obj if item is not None]
    
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                key = str(key)
            converted = _convert_to_primitives(value, depth+1)
            if converted is not None:
                result[key] = converted
        return result
    
    # Everything else - convert to string as last resort
    try:
        str_val = str(obj)
        # Validate it's actually JSON-serializable
        json.dumps(str_val)
        return str_val
    except Exception:
        return None
