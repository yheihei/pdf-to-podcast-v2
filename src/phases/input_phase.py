import os
from typing import Optional, Tuple
import PyPDF2
import pdfplumber
from ..utils import setup_logger

logger = setup_logger(__name__)

class InputPhase:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def process_pdf(self, pdf_path: str, start_page: Optional[int] = None, 
                   end_page: Optional[int] = None) -> str:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Processing PDF: {pdf_path}")
        
        text_content = self._extract_pdf_text(pdf_path, start_page, end_page)
        
        output_path = os.path.join(self.output_dir, "input_text.txt")
        self._save_text(text_content, output_path)
        
        logger.info(f"Extracted text saved to: {output_path}")
        return output_path
    
    def process_text(self, text_path: str) -> str:
        if not os.path.exists(text_path):
            raise FileNotFoundError(f"Text file not found: {text_path}")
        
        logger.info(f"Processing text file: {text_path}")
        
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        text_content = self._clean_text(text_content)
        
        output_path = os.path.join(self.output_dir, "input_text.txt")
        self._save_text(text_content, output_path)
        
        logger.info(f"Text content saved to: {output_path}")
        return output_path
    
    def _extract_pdf_text(self, pdf_path: str, start_page: Optional[int], 
                         end_page: Optional[int]) -> str:
        text_parts = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                start_idx = (start_page - 1) if start_page else 0
                end_idx = end_page if end_page else total_pages
                
                start_idx = max(0, min(start_idx, total_pages - 1))
                end_idx = max(start_idx + 1, min(end_idx, total_pages))
                
                logger.info(f"Extracting pages {start_idx + 1} to {end_idx} of {total_pages}")
                
                for i in range(start_idx, end_idx):
                    page = pdf.pages[i]
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                    logger.debug(f"Extracted page {i + 1}")
        
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, trying PyPDF2")
            text_parts = self._extract_with_pypdf2(pdf_path, start_page, end_page)
        
        full_text = "\n\n".join(text_parts)
        return self._clean_text(full_text)
    
    def _extract_with_pypdf2(self, pdf_path: str, start_page: Optional[int], 
                            end_page: Optional[int]) -> list:
        text_parts = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            start_idx = (start_page - 1) if start_page else 0
            end_idx = end_page if end_page else total_pages
            
            start_idx = max(0, min(start_idx, total_pages - 1))
            end_idx = max(start_idx + 1, min(end_idx, total_pages))
            
            for i in range(start_idx, end_idx):
                page = pdf_reader.pages[i]
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return text_parts
    
    def _clean_text(self, text: str) -> str:
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        paragraphs = []
        current_paragraph = []
        
        for line in cleaned_lines:
            if not line:
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return '\n\n'.join(paragraphs)
    
    def _save_text(self, text: str, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        logger.info(f"Saved {len(text)} characters to {output_path}")