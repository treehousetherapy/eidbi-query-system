"""
PDF Processing Utility for Enhanced EIDBI Scraper

This module provides robust PDF text extraction capabilities using multiple
extraction methods with fallback options and comprehensive error handling.

Features:
- Multiple extraction methods (pdfplumber, PyPDF2)
- Metadata extraction
- Page-by-page processing
- Error recovery and logging
- Content validation

Author: Enhanced EIDBI Scraper
"""

import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from io import BytesIO
from pathlib import Path

# PDF processing libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logging.warning("PyPDF2 not available. Install with: pip install PyPDF2")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logging.warning("pdfplumber not available. Install with: pip install pdfplumber")

logger = logging.getLogger(__name__)

class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors"""
    pass

class PDFProcessor:
    """
    Enhanced PDF processor with multiple extraction methods and robust error handling
    """
    
    def __init__(self):
        self.extraction_methods = []
        
        # Determine available extraction methods
        if PDFPLUMBER_AVAILABLE:
            self.extraction_methods.append('pdfplumber')
        if PYPDF2_AVAILABLE:
            self.extraction_methods.append('pypdf2')
            
        if not self.extraction_methods:
            raise PDFProcessingError("No PDF processing libraries available. Install PyPDF2 or pdfplumber.")
        
        logger.info(f"PDF Processor initialized with methods: {self.extraction_methods}")
    
    def extract_with_pdfplumber(self, pdf_content: bytes, url: str = "") -> Dict[str, Any]:
        """
        Extract text using pdfplumber (preferred method for layout preservation)
        
        Args:
            pdf_content: Raw PDF content as bytes
            url: URL of the PDF for logging purposes
            
        Returns:
            Dictionary with extraction results
        """
        if not PDFPLUMBER_AVAILABLE:
            raise PDFProcessingError("pdfplumber not available")
        
        results = {
            'text': '',
            'metadata': {},
            'page_count': 0,
            'pages': [],
            'extraction_method': 'pdfplumber',
            'success': False,
            'errors': []
        }
        
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                text_parts = []
                page_info = []
                
                # Process each page
                for page_num, page in enumerate(pdf.pages):
                    page_result = {
                        'page_number': page_num + 1,
                        'text': '',
                        'char_count': 0,
                        'word_count': 0,
                        'success': False
                    }
                    
                    try:
                        # Extract text from page
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            # Clean and format page text
                            cleaned_text = self._clean_extracted_text(page_text)
                            page_result.update({
                                'text': cleaned_text,
                                'char_count': len(cleaned_text),
                                'word_count': len(cleaned_text.split()),
                                'success': True
                            })
                            
                            # Add page separator and text
                            formatted_page = f"\n{'='*60}\nPage {page_num + 1}\n{'='*60}\n{cleaned_text}"
                            text_parts.append(formatted_page)
                            
                            logger.debug(f"Extracted {len(cleaned_text)} characters from page {page_num + 1}")
                        else:
                            logger.warning(f"No readable text found on page {page_num + 1} of {url}")
                            page_result['errors'] = ['No readable text found']
                    
                    except Exception as e:
                        error_msg = f"Error extracting page {page_num + 1}: {str(e)}"
                        logger.warning(error_msg)
                        page_result['errors'] = [error_msg]
                        results['errors'].append(error_msg)
                    
                    page_info.append(page_result)
                
                # Compile results
                if text_parts:
                    results.update({
                        'text': '\n'.join(text_parts),
                        'page_count': len(pdf.pages),
                        'pages': page_info,
                        'success': True
                    })
                    
                    # Extract PDF metadata
                    if hasattr(pdf, 'metadata') and pdf.metadata:
                        results['metadata'] = self._clean_metadata(dict(pdf.metadata))
                    
                    successful_pages = sum(1 for page in page_info if page['success'])
                    logger.info(f"pdfplumber: Successfully extracted {successful_pages}/{len(pdf.pages)} pages")
                else:
                    results['errors'].append("No text could be extracted from any page")
                    
        except Exception as e:
            error_msg = f"pdfplumber extraction failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            raise PDFProcessingError(error_msg)
        
        return results
    
    def extract_with_pypdf2(self, pdf_content: bytes, url: str = "") -> Dict[str, Any]:
        """
        Extract text using PyPDF2 (fallback method)
        
        Args:
            pdf_content: Raw PDF content as bytes
            url: URL of the PDF for logging purposes
            
        Returns:
            Dictionary with extraction results
        """
        if not PYPDF2_AVAILABLE:
            raise PDFProcessingError("PyPDF2 not available")
        
        results = {
            'text': '',
            'metadata': {},
            'page_count': 0,
            'pages': [],
            'extraction_method': 'pypdf2',
            'success': False,
            'errors': []
        }
        
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text_parts = []
            page_info = []
            
            # Process each page
            for page_num in range(len(pdf_reader.pages)):
                page_result = {
                    'page_number': page_num + 1,
                    'text': '',
                    'char_count': 0,
                    'word_count': 0,
                    'success': False
                }
                
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        # Clean and format page text
                        cleaned_text = self._clean_extracted_text(page_text)
                        page_result.update({
                            'text': cleaned_text,
                            'char_count': len(cleaned_text),
                            'word_count': len(cleaned_text.split()),
                            'success': True
                        })
                        
                        # Add page separator and text
                        formatted_page = f"\n{'='*60}\nPage {page_num + 1}\n{'='*60}\n{cleaned_text}"
                        text_parts.append(formatted_page)
                        
                        logger.debug(f"Extracted {len(cleaned_text)} characters from page {page_num + 1}")
                    else:
                        logger.warning(f"No readable text found on page {page_num + 1} of {url}")
                        page_result['errors'] = ['No readable text found']
                        
                except Exception as e:
                    error_msg = f"Error extracting page {page_num + 1}: {str(e)}"
                    logger.warning(error_msg)
                    page_result['errors'] = [error_msg]
                    results['errors'].append(error_msg)
                
                page_info.append(page_result)
            
            # Compile results
            if text_parts:
                results.update({
                    'text': '\n'.join(text_parts),
                    'page_count': len(pdf_reader.pages),
                    'pages': page_info,
                    'success': True
                })
                
                # Extract PDF metadata
                if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                    raw_metadata = {
                        k.replace('/', ''): v for k, v in pdf_reader.metadata.items()
                    }
                    results['metadata'] = self._clean_metadata(raw_metadata)
                
                successful_pages = sum(1 for page in page_info if page['success'])
                logger.info(f"PyPDF2: Successfully extracted {successful_pages}/{len(pdf_reader.pages)} pages")
            else:
                results['errors'].append("No text could be extracted from any page")
                
        except Exception as e:
            error_msg = f"PyPDF2 extraction failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            raise PDFProcessingError(error_msg)
        
        return results
    
    def extract_text(self, pdf_content: bytes, url: str = "", preferred_method: str = None) -> Dict[str, Any]:
        """
        Extract text from PDF using the best available method
        
        Args:
            pdf_content: Raw PDF content as bytes
            url: URL of the PDF for logging purposes
            preferred_method: Preferred extraction method ('pdfplumber' or 'pypdf2')
            
        Returns:
            Dictionary with extraction results
        """
        if not pdf_content:
            raise PDFProcessingError("No PDF content provided")
        
        # Validate PDF content
        if not self._is_valid_pdf(pdf_content):
            raise PDFProcessingError("Invalid PDF content")
        
        # Calculate checksum for tracking
        checksum = hashlib.md5(pdf_content).hexdigest()
        
        # Determine extraction order
        methods_to_try = []
        if preferred_method and preferred_method in self.extraction_methods:
            methods_to_try.append(preferred_method)
            # Add other methods as fallbacks
            methods_to_try.extend([m for m in self.extraction_methods if m != preferred_method])
        else:
            # Use default order: pdfplumber first (better layout preservation), then PyPDF2
            methods_to_try = self.extraction_methods[:]
        
        last_error = None
        all_errors = []
        
        for method in methods_to_try:
            try:
                logger.info(f"Attempting PDF extraction with {method} for {url or 'unknown source'}")
                
                if method == 'pdfplumber':
                    result = self.extract_with_pdfplumber(pdf_content, url)
                elif method == 'pypdf2':
                    result = self.extract_with_pypdf2(pdf_content, url)
                else:
                    continue
                
                if result['success'] and result['text'].strip():
                    # Add processing metadata
                    result['checksum'] = checksum
                    result['file_size'] = len(pdf_content)
                    result['extraction_attempts'] = len(all_errors) + 1
                    result['fallback_errors'] = all_errors
                    
                    logger.info(f"Successfully extracted PDF text using {method}: "
                               f"{len(result['text'])} characters from {result['page_count']} pages")
                    return result
                else:
                    error_msg = f"{method} extraction returned no usable text"
                    all_errors.extend(result.get('errors', [error_msg]))
                    logger.warning(error_msg)
                    
            except PDFProcessingError as e:
                error_msg = f"{method} failed: {str(e)}"
                all_errors.append(error_msg)
                last_error = e
                logger.warning(error_msg)
                continue
            except Exception as e:
                error_msg = f"Unexpected error with {method}: {str(e)}"
                all_errors.append(error_msg)
                last_error = e
                logger.error(error_msg, exc_info=True)
                continue
        
        # All methods failed
        error_summary = f"All PDF extraction methods failed for {url or 'unknown source'}. Errors: {'; '.join(all_errors)}"
        logger.error(error_summary)
        
        return {
            'text': '',
            'metadata': {},
            'page_count': 0,
            'pages': [],
            'extraction_method': None,
            'success': False,
            'errors': all_errors,
            'checksum': checksum,
            'file_size': len(pdf_content)
        }
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace while preserving paragraph structure
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace from each line
            line = line.strip()
            
            # Skip empty lines in sequence (keep only one)
            if not line:
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
            else:
                # Replace multiple spaces with single space
                line = ' '.join(line.split())
                cleaned_lines.append(line)
        
        # Join lines and remove trailing empty lines
        cleaned_text = '\n'.join(cleaned_lines).strip()
        
        # Remove excessive line breaks (more than 2 consecutive)
        import re
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize PDF metadata
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        
        for key, value in metadata.items():
            if value is None:
                continue
            
            # Clean key name
            clean_key = str(key).strip().replace('/', '').replace('\\', '')
            
            # Clean value
            if isinstance(value, str):
                clean_value = value.strip()
                if clean_value:
                    cleaned[clean_key] = clean_value
            else:
                cleaned[clean_key] = value
        
        return cleaned
    
    def _is_valid_pdf(self, pdf_content: bytes) -> bool:
        """
        Check if content appears to be a valid PDF
        
        Args:
            pdf_content: Raw content to check
            
        Returns:
            True if appears to be valid PDF
        """
        if not pdf_content or len(pdf_content) < 5:
            return False
        
        # Check PDF header
        return pdf_content.startswith(b'%PDF-')
    
    def get_pdf_info(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Get basic information about a PDF without full text extraction
        
        Args:
            pdf_content: Raw PDF content as bytes
            
        Returns:
            Dictionary with PDF information
        """
        info = {
            'file_size': len(pdf_content),
            'checksum': hashlib.md5(pdf_content).hexdigest(),
            'is_valid': self._is_valid_pdf(pdf_content),
            'page_count': 0,
            'metadata': {},
            'readable': False
        }
        
        if not info['is_valid']:
            return info
        
        # Try to get basic info with minimal processing
        for method in self.extraction_methods:
            try:
                if method == 'pdfplumber' and PDFPLUMBER_AVAILABLE:
                    with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                        info['page_count'] = len(pdf.pages)
                        if hasattr(pdf, 'metadata') and pdf.metadata:
                            info['metadata'] = self._clean_metadata(dict(pdf.metadata))
                        # Test if first page has readable text
                        if pdf.pages and len(pdf.pages) > 0:
                            try:
                                first_page_text = pdf.pages[0].extract_text()
                                info['readable'] = bool(first_page_text and first_page_text.strip())
                            except:
                                pass
                        break
                        
                elif method == 'pypdf2' and PYPDF2_AVAILABLE:
                    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
                    info['page_count'] = len(pdf_reader.pages)
                    if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                        raw_metadata = {
                            k.replace('/', ''): v for k, v in pdf_reader.metadata.items()
                        }
                        info['metadata'] = self._clean_metadata(raw_metadata)
                    # Test if first page has readable text
                    if pdf_reader.pages and len(pdf_reader.pages) > 0:
                        try:
                            first_page_text = pdf_reader.pages[0].extract_text()
                            info['readable'] = bool(first_page_text and first_page_text.strip())
                        except:
                            pass
                    break
                    
            except Exception as e:
                logger.debug(f"Error getting PDF info with {method}: {e}")
                continue
        
        return info

# Convenience function for simple usage
def extract_pdf_text(pdf_content: bytes, url: str = "", preferred_method: str = None) -> Dict[str, Any]:
    """
    Convenience function to extract text from PDF
    
    Args:
        pdf_content: Raw PDF content as bytes
        url: URL of the PDF for logging purposes
        preferred_method: Preferred extraction method ('pdfplumber' or 'pypdf2')
        
    Returns:
        Dictionary with extraction results
    """
    processor = PDFProcessor()
    return processor.extract_text(pdf_content, url, preferred_method) 