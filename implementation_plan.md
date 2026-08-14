# PDF Tools Suite — Implementation Plan

## Overview

Add a comprehensive **PDF Tools Suite** to BR JARVIS, covering all 30+ PDF operations listed by the user. These tools will be implemented as a new `tools/pdf_tools.py` module registered into the existing `ToolRegistry` plugin system — following the same pattern as `doc_tools.py`, `excel_tools.py`, etc.

All required Python libraries are **already present** in `requirements.txt`:
- `pypdf` — merge, split, rotate, protect, unlock, organize, page numbers, repair
- `PyMuPDF` (fitz) — compress, extract images, OCR, crop, redact, compare, PDF/A
- `python-docx` — PDF to Word / Word to PDF
- `python-pptx` — PDF to PowerPoint / PowerPoint to PDF
- `openpyxl` — PDF to Excel / Excel to PDF
- `Pillow` — JPG ↔ PDF, image watermarks
- `fpdf2` — HTML to PDF, watermark stamps

---

## Proposed Changes

### New File

#### [NEW] [pdf_tools.py](file:///d:/BRJARVIS/Br-Jarvis/tools/pdf_tools.py)

A single comprehensive module with one unified `pdf_tool` registered function, dispatched by an `action` argument. Covers all 30+ operations:

| Action | Description |
|--------|-------------|
| `merge` | Merge multiple PDFs in specified order |
| `split` | Split PDF into individual pages or page ranges |
| `compress` | Reduce file size with quality optimization |
| `pdf_to_word` | Convert PDF → DOCX |
| `pdf_to_powerpoint` | Convert PDF → PPTX |
| `pdf_to_excel` | Extract tables from PDF → XLSX |
| `word_to_pdf` | Convert DOCX → PDF |
| `powerpoint_to_pdf` | Convert PPTX → PDF |
| `excel_to_pdf` | Convert XLSX → PDF |
| `edit_pdf` | Add text/annotations to PDF pages |
| `pdf_to_jpg` | Convert PDF pages to JPG images |
| `jpg_to_pdf` | Convert JPG images to PDF |
| `watermark` | Stamp text or image watermark on PDF |
| `rotate` | Rotate PDF pages |
| `html_to_pdf` | Convert HTML content or URL to PDF |
| `unlock` | Remove PDF password protection |
| `protect` | Add password protection to PDF |
| `organize` | Reorder, delete, or insert pages |
| `pdf_to_pdfa` | Convert to PDF/A archival format |
| `repair` | Attempt to repair and recover corrupted PDF |
| `page_numbers` | Add page numbers at specified position |
| `ocr` | OCR scanned PDF to searchable text |
| `compare` | Side-by-side diff of two PDF versions |
| `redact` | Permanently redact sensitive text/areas |
| `crop` | Crop margins or select region of pages |
| `pdf_forms` | Detect and fill PDF form fields |
| `summarize` | AI-powered summary of PDF content |
| `translate` | Translate PDF text (using AI backend) |
| `pdf_to_markdown` | Convert PDF structure to Markdown |
| `sign` | Add digital signature placeholder to PDF |

---

### Modified Files

#### [MODIFY] [registry.py](file:///d:/BRJARVIS/Br-Jarvis/tools/registry.py)

1. Add `"tools.pdf_tools"` to the `extended_plugins` list so it auto-loads on demand.
2. Add `"pdf_tool": "tools.pdf_tools"` entry in the `tool_to_module` lazy-load map.
3. Add `("pdf", "merge pdf", "split pdf", "compress pdf", "ocr", "watermark", "sign pdf", "rotate pdf")` keywords → `{"pdf_tool"}` in the `domain_map` of `get_pruned_tool_prompt_block`.

#### [MODIFY] [requirements.txt](file:///d:/BRJARVIS/Br-Jarvis/requirements.txt)

Add `pikepdf>=9.0.0,<10.0.0` for more robust PDF repair/unlock operations (optional enhancement). All other deps are already present.

---

## Architecture Design

```
pdf_tool(action, input_path, output_path?, pages?, password?, ...)
         │
         ├── merge        → pypdf PdfWriter
         ├── split        → pypdf PdfWriter per page
         ├── compress     → PyMuPDF fitz.open().save(deflate=True)
         ├── pdf_to_word  → PyMuPDF text extraction → python-docx
         ├── pdf_to_pptx  → PyMuPDF page render → python-pptx slide
         ├── pdf_to_excel → PyMuPDF table detection → openpyxl
         ├── word_to_pdf  → python-docx → fpdf2 or subprocess LibreOffice
         ├── edit_pdf     → PyMuPDF annotation insertion
         ├── pdf_to_jpg   → PyMuPDF pixmap render
         ├── jpg_to_pdf   → Pillow → fpdf2
         ├── watermark    → PyMuPDF text/image overlay
         ├── rotate       → pypdf rotate
         ├── html_to_pdf  → fpdf2 HTMLMixin
         ├── unlock       → pypdf decrypt
         ├── protect      → pypdf encrypt
         ├── organize     → pypdf page reorder/delete
         ├── pdf_to_pdfa  → PyMuPDF convert
         ├── repair       → pypdf strict=False reader
         ├── page_numbers → PyMuPDF annotation
         ├── ocr          → PyMuPDF + tesseract (optional)
         ├── compare      → PyMuPDF text diff
         ├── redact       → PyMuPDF redaction
         ├── crop         → PyMuPDF set_cropbox
         ├── pdf_forms    → pypdf/PyMuPDF form field access
         ├── summarize    → text extract → AI summarize
         ├── translate    → text extract → AI translate
         ├── pdf_to_md    → PyMuPDF text + structure → Markdown
         └── sign         → PyMuPDF signature widget
```

---

## Verification Plan

### Automated Tests
- Quick import check: `python -c "import tools.pdf_tools; print('OK')"`
- Tool registration: verify `pdf_tool` appears in `TOOL_REGISTRY`

### Manual Verification
- Test `merge` with 2 sample PDFs in workspace
- Test `split` on a multi-page PDF
- Test `compress` and compare file sizes
- Test `pdf_to_word` extraction quality
- Test `watermark` with text stamp
- Test `protect` and `unlock` round-trip
