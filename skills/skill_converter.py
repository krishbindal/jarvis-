"""
JARVIS-X Phase 30: Format Master (Conversion Skill)
Local Word to PDF conversion powered by docx2pdf.
"""

from __future__ import annotations

import os
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("SKILL_CONVERTER")

def convert_word_to_pdf(docx_path: str) -> dict:
    """Converts a Word .docx file into a .pdf file."""
    try:
        from docx2pdf import convert
        
        input_path = Path(docx_path)
        if not input_path.exists():
            return {"success": False, "message": f"File not found: {docx_path}"}
        
        output_path = input_path.with_suffix(".pdf")
        
        logger.info(f"[CONVERTER] Converting {input_path.name} to PDF...")
        # docx2pdf.convert(input, output)
        # Note: requires Microsoft Word to be installed on the system for best results
        convert(str(input_path), str(output_path))
        
        if output_path.exists():
            logger.info(f"[CONVERTER] Success: Generated {output_path.name}")
            return {
                "success": True, 
                "message": f"Successfully converted to {output_path.name}",
                "pdf_path": str(output_path)
            }
        return {"success": False, "message": "Conversion failed: output file not created."}
        
    except Exception as e:
        logger.error(f"[CONVERTER] Failure: {e}")
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        print(convert_word_to_pdf(sys.argv[1]))
