# ============================================
# OCR Engine for Scanned DPR Documents
# Supports Indian Regional Languages
# ============================================

from pathlib import Path
from typing import Optional, Union

from PIL import Image
from loguru import logger

from config.settings import settings


class OCREngine:
    """
    OCR processing for scanned DPR documents.
    Supports English + 9 Indian regional languages.
    Uses EasyOCR for multilingual support.
    """

    # Language mapping for Indian languages
    LANGUAGE_MAP = {
        "hindi": "hi",
        "telugu": "te",
        "tamil": "ta",
        "kannada": "kn",
        "malayalam": "ml",
        "bengali": "bn",
        "gujarati": "gu",
        "marathi": "mr",
        "odia": "or",
        "punjabi": "pa",
        "assamese": "as",
        "english": "en"
    }

    # State to primary language mapping
    STATE_LANGUAGE_MAP = {
        "Andhra Pradesh": ["te", "en"],
        "Arunachal Pradesh": ["en", "hi"],
        "Assam": ["as", "en"],
        "Bihar": ["hi", "en"],
        "Chhattisgarh": ["hi", "en"],
        "Goa": ["en", "hi"],
        "Gujarat": ["gu", "en"],
        "Haryana": ["hi", "en"],
        "Himachal Pradesh": ["hi", "en"],
        "Jharkhand": ["hi", "en"],
        "Karnataka": ["kn", "en"],
        "Kerala": ["ml", "en"],
        "Madhya Pradesh": ["hi", "en"],
        "Maharashtra": ["mr", "en"],
        "Manipur": ["en", "hi"],
        "Meghalaya": ["en"],
        "Mizoram": ["en"],
        "Nagaland": ["en"],
        "Odisha": ["or", "en"],
        "Punjab": ["pa", "en"],
        "Rajasthan": ["hi", "en"],
        "Sikkim": ["en", "hi"],
        "Tamil Nadu": ["ta", "en"],
        "Telangana": ["te", "en"],
        "Tripura": ["bn", "en"],
        "Uttar Pradesh": ["hi", "en"],
        "Uttarakhand": ["hi", "en"],
        "West Bengal": ["bn", "en"],
    }

    def __init__(self):
        self._easyocr_reader = None
        self._current_langs = None
        logger.info("OCREngine initialized")

    def _get_easyocr_reader(self, languages: list):
        """Lazy-load EasyOCR reader with specified languages."""
        try:
            import easyocr
            if self._easyocr_reader is None or self._current_langs != languages:
                self._easyocr_reader = easyocr.Reader(languages, gpu=False)
                self._current_langs = languages
                logger.info(f"EasyOCR reader loaded for languages: {languages}")
            return self._easyocr_reader
        except ImportError:
            logger.error("EasyOCR not installed. Install with: pip install easyocr")
            return None

    def extract_text_from_image(
        self,
        image_path: Union[str, Path],
        languages: Optional[list] = None,
        state: Optional[str] = None
    ) -> dict:
        """
        Extract text from an image file using OCR.

        Args:
            image_path: Path to the image file
            languages: List of language codes (e.g., ['en', 'hi'])
            state: Indian state name to auto-detect language

        Returns:
            dict with extracted text and metadata
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Determine languages
        if languages is None:
            if state and state in self.STATE_LANGUAGE_MAP:
                languages = self.STATE_LANGUAGE_MAP[state]
            else:
                languages = ["en"]

        result = {
            "file_name": image_path.name,
            "languages_used": languages,
            "state": state,
            "full_text": "",
            "text_blocks": [],
            "confidence_scores": [],
            "ocr_engine": "easyocr"
        }

        reader = self._get_easyocr_reader(languages)
        if reader is None:
            result["error"] = "OCR engine not available"
            return result

        try:
            ocr_results = reader.readtext(str(image_path))

            for bbox, text, confidence in ocr_results:
                result["text_blocks"].append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "bounding_box": bbox
                })
                result["confidence_scores"].append(confidence)

            result["full_text"] = " ".join([block["text"] for block in result["text_blocks"]])
            result["average_confidence"] = (
                round(sum(result["confidence_scores"]) / len(result["confidence_scores"]), 4)
                if result["confidence_scores"] else 0
            )
            result["total_text_blocks"] = len(result["text_blocks"])

            logger.info(
                f"OCR extracted {len(result['text_blocks'])} text blocks "
                f"with avg confidence {result['average_confidence']}"
            )

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            result["error"] = str(e)

        return result

    def extract_text_from_pdf_images(
        self,
        pdf_path: Union[str, Path],
        languages: Optional[list] = None,
        state: Optional[str] = None
    ) -> dict:
        """
        Extract text from scanned PDF by converting pages to images.
        """
        import tempfile
        from pdf2image import convert_from_path

        pdf_path = Path(pdf_path)
        result = {
            "file_name": pdf_path.name,
            "page_texts": [],
            "full_text": "",
            "total_pages": 0
        }

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                images = convert_from_path(str(pdf_path), output_folder=tmp_dir)
                result["total_pages"] = len(images)

                for i, image in enumerate(images):
                    img_path = Path(tmp_dir) / f"page_{i + 1}.png"
                    image.save(str(img_path), "PNG")

                    page_result = self.extract_text_from_image(
                        str(img_path), languages=languages, state=state
                    )
                    result["page_texts"].append({
                        "page_number": i + 1,
                        "text": page_result.get("full_text", ""),
                        "confidence": page_result.get("average_confidence", 0)
                    })

                result["full_text"] = "\n\n".join(
                    [p["text"] for p in result["page_texts"]]
                )

            logger.info(f"OCR completed for {result['total_pages']} pages")

        except ImportError:
            logger.error("pdf2image not installed. Install with: pip install pdf2image")
            result["error"] = "pdf2image library required for scanned PDF OCR"
        except Exception as e:
            logger.error(f"PDF OCR failed: {e}")
            result["error"] = str(e)

        return result

    def preprocess_image(self, image_path: str) -> str:
        """
        Preprocess image for better OCR accuracy.
        Applies: grayscale, denoising, thresholding, deskewing.
        """
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Save processed image
        output_path = image_path.replace(".", "_processed.")
        cv2.imwrite(output_path, binary)

        logger.info(f"Image preprocessed and saved to {output_path}")
        return output_path

    def detect_language(self, text: str) -> dict:
        """Detect the language of extracted text."""
        from langdetect import detect, detect_langs

        try:
            primary = detect(text)
            all_langs = detect_langs(text)
            return {
                "primary_language": primary,
                "detected_languages": [
                    {"lang": str(lang).split(":")[0], "probability": float(str(lang).split(":")[1])}
                    for lang in all_langs
                ]
            }
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {"primary_language": "unknown", "detected_languages": []}
