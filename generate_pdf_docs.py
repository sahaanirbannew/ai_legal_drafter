#!/usr/bin/env python3
"""
Convert documentation markdown to PDF with architecture diagrams
Requires: pip install markdown2 pdfkit wkhtmltopdf
"""

import os
import sys
from datetime import datetime

# Try to import required libraries
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
except ImportError:
    print("Error: reportlab not installed. Run: pip install reportlab")
    sys.exit(1)


def create_pdf_documentation():
    """Generate comprehensive PDF documentation"""
    
    # Output path
    output_path = os.path.expanduser("~/Downloads/AI_Legal_Arguments_Documentation.pdf")
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=24,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2e5c8a'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#3d7ca8'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )
    
    # ===== TITLE PAGE =====
    elements.append(Spacer(1, 1.5*inch))
    elements.append(Paragraph("AI Legal Arguments Generator", title_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Complete Technical Documentation", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", body_style))
    elements.append(Spacer(1, 1*inch))
    
    # Executive Summary
    elements.append(Paragraph("Executive Summary", heading1_style))
    elements.append(Paragraph(
        "The AI Legal Arguments Generator is a web-based application that leverages artificial intelligence "
        "(OpenAI GPT-5 and Google Gemini 1.5) to analyze legal case documents, generate sophisticated legal arguments, "
        "identify relevant citations, and validate the quality of legal reasoning for Indian constitutional law cases.",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== TABLE OF CONTENTS =====
    elements.append(Paragraph("Table of Contents", heading1_style))
    toc_items = [
        "1. Project Overview",
        "2. System Architecture",
        "3. Technology Stack",
        "4. API Endpoints",
        "5. Data Flow",
        "6. Component Descriptions",
        "7. Setup and Configuration",
        "8. User Workflow",
        "9. File Structure",
        "10. Dependencies and Deployment"
    ]
    for item in toc_items:
        elements.append(Paragraph(item, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== PROJECT OVERVIEW =====
    elements.append(Paragraph("1. Project Overview", heading1_style))
    
    elements.append(Paragraph("Objectives", heading2_style))
    objectives = [
        "• Automated Legal Analysis: Parse and analyze legal case documents using AI",
        "• Argument Generation: Generate compelling legal arguments with reasoning",
        "• Citation Intelligence: Identify and suggest relevant Supreme Court/High Court citations",
        "• Quality Validation: Validate generated arguments for logical consistency",
        "• PDF Export: Generate downloadable legal argument documents with timestamps"
    ]
    for obj in objectives:
        elements.append(Paragraph(obj, body_style))
    elements.append(Spacer(1, 0.15*inch))
    
    elements.append(Paragraph("Key Features", heading2_style))
    features = [
        "✓ PDF Case Upload with real-time status",
        "✓ AI-Powered Analysis using OpenAI GPT-5",
        "✓ Legal Citation Discovery and Validation",
        "✓ Gemini-based Quality Validation",
        "✓ Dynamic PDF Generation with Timestamps",
        "✓ Responsive Web Interface"
    ]
    for feat in features:
        elements.append(Paragraph(feat, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== SYSTEM ARCHITECTURE =====
    elements.append(Paragraph("2. System Architecture", heading1_style))
    
    arch_text = """
    The system follows a three-tier architecture:
    
    <b>Frontend Tier:</b> HTML5 + Vanilla JavaScript providing user interface for:
    • Case document upload
    • Real-time status updates
    • Analysis results display
    • Citation details viewing
    • Validation results
    • PDF export
    
    <b>API Tier:</b> FastAPI backend handling:
    • HTTP routing and endpoint management
    • OpenAI integration
    • Gemini integration
    • File management
    • PDF generation
    
    <b>Integration Tier:</b> External AI services:
    • OpenAI GPT-5 for case analysis
    • Google Gemini 1.5 Pro for validation
    • Local PDF storage
    """
    
    elements.append(Paragraph(arch_text, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== TECHNOLOGY STACK =====
    elements.append(Paragraph("3. Technology Stack", heading1_style))
    
    # Create tech stack table
    tech_data = [
        ['Layer', 'Technology', 'Purpose'],
        ['Frontend', 'HTML5, CSS, JavaScript', 'User interface'],
        ['Backend', 'FastAPI, Uvicorn', 'REST API server'],
        ['AI Services', 'OpenAI GPT-5, Gemini 1.5', 'Legal analysis'],
        ['PDF Generation', 'ReportLab', 'PDF creation'],
        ['File Handling', 'Python multipart', 'Upload processing'],
        ['Environment', 'python-dotenv', 'Configuration management'],
        ['Runtime', 'Python 3.9.6', 'Execution environment']
    ]
    
    tech_table = Table(tech_data, colWidths=[1.5*inch, 2*inch, 2*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5c8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4f8')])
    ]))
    
    elements.append(tech_table)
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== API ENDPOINTS =====
    elements.append(Paragraph("4. API Endpoints", heading1_style))
    
    endpoints = [
        ("GET /", "Serve Homepage", "Returns HTML interface"),
        ("POST /upload", "Upload Case PDF", "Register case with OpenAI"),
        ("POST /analyze", "Analyze Case", "Generate arguments and citations"),
        ("POST /validate", "Validate Arguments", "Quality check with Gemini"),
        ("POST /generate_pdf", "Export to PDF", "Create timestamped download")
    ]
    
    for method, name, desc in endpoints:
        elements.append(Paragraph(f"<b>{method} - {name}</b>", heading2_style))
        elements.append(Paragraph(f"Purpose: {desc}", body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== DATA FLOW =====
    elements.append(Paragraph("5. Data Flow", heading1_style))
    
    flow_text = """
    <b>Step 1: Upload</b>
    User → /upload endpoint → Save to uploads/ → Create OpenAI file → Store file_id
    
    <b>Step 2: Analyze</b>
    /analyze endpoint → OpenAI API (file_id) → Parse JSON response → Store case_json_store
    → build_argument() → generated_text → Return to frontend
    
    <b>Step 3: Validate</b>
    /validate endpoint → Gemini API (original PDF + args PDF) → Validation report
    → Append to generated_text → Create validated PDF
    
    <b>Step 4: Export</b>
    /generate_pdf endpoint → Generate timestamp → Create filename → Save to ~/Downloads
    → Return file as download
    """
    
    elements.append(Paragraph(flow_text, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== COMPONENTS =====
    elements.append(Paragraph("6. Component Descriptions", heading1_style))
    
    components = {
        "main.py": "FastAPI backend managing HTTP routing, OpenAI integration, and state management",
        "openai_client.py": "OpenAI API integration handling case analysis and citation extraction",
        "gemini_validator.py": "Google Gemini integration for validation and hallucination detection",
        "prompt.py": "Converts JSON analysis results to human-readable legal documents",
        "pdf_generator.py": "ReportLab integration for creating branded PDF documents",
        "index.html": "Web interface with file upload, display areas, and controls",
        "script.js": "Frontend JavaScript managing user interactions and API calls"
    }
    
    for component, description in components.items():
        elements.append(Paragraph(f"<b>{component}</b>", heading2_style))
        elements.append(Paragraph(description, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== SETUP =====
    elements.append(Paragraph("7. Setup and Configuration", heading1_style))
    
    setup_steps = [
        "1. Create virtual environment: python -m venv .venv",
        "2. Activate: source .venv/bin/activate",
        "3. Install dependencies: pip install -r requirements.txt",
        "4. Create .env file with API keys",
        "5. Run server: python -m uvicorn main:app --reload",
        "6. Open: http://localhost:8000"
    ]
    
    for step in setup_steps:
        elements.append(Paragraph(step, body_style))
    elements.append(Spacer(1, 0.15*inch))
    
    elements.append(Paragraph("Environment Variables (.env)", heading2_style))
    elements.append(Paragraph("OPENAI_API_KEY=sk-...", body_style))
    elements.append(Paragraph("GEMINI_API_KEY=AIzaSy...", body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== USER WORKFLOW =====
    elements.append(Paragraph("8. User Workflow", heading1_style))
    
    workflow_steps = [
        ("<b>Step 1: Upload</b>", "Select PDF → Click Upload → See 'Uploaded' status"),
        ("<b>Step 2: Generate</b>", "Click Generate → See 'Generating...' → View results"),
        ("<b>Step 3: Validate</b>", "Click Validate with Gemini → Review validation report"),
        ("<b>Step 4: Export</b>", "Click Generate PDF → File saved to ~/Downloads")
    ]
    
    for step_name, step_desc in workflow_steps:
        elements.append(Paragraph(f"{step_name}: {step_desc}", body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== FILE STRUCTURE =====
    elements.append(Paragraph("9. File Structure", heading1_style))
    
    file_structure = """
    ai_legal_arguments/
    ├── main.py                    (FastAPI backend)
    ├── openai_client.py          (OpenAI integration)
    ├── gemini_validator.py       (Gemini validation)
    ├── prompt.py                 (Argument formatting)
    ├── pdf_generator.py          (PDF creation)
    ├── requirements.txt          (Dependencies)
    ├── .env                      (API credentials)
    ├── templates/
    │   └── index.html            (Web interface)
    ├── static/
    │   └── script.js             (Frontend logic)
    ├── uploads/                  (Uploaded PDFs)
    └── DOCUMENTATION.md          (Full documentation)
    """
    
    elements.append(Paragraph(file_structure, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(PageBreak())
    
    # ===== DEPENDENCIES =====
    elements.append(Paragraph("10. Dependencies and Deployment", heading1_style))
    
    elements.append(Paragraph("Required Libraries", heading2_style))
    deps = [
        "fastapi - Web framework for building APIs",
        "uvicorn - ASGI server for running FastAPI",
        "openai - Official OpenAI Python client",
        "google-generativeai - Google Gemini API client",
        "python-multipart - Form data handling",
        "reportlab - PDF generation library",
        "python-dotenv - Environment variable management",
        "jinja2 - Template engine",
        "faiss-cpu - Vector search (future)",
        "tiktoken - Token counting for GPT models"
    ]
    
    for dep in deps:
        elements.append(Paragraph(f"• {dep}", body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Add footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        f"<i>Document Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</i>",
        body_style
    ))
    elements.append(Paragraph(
        "AI Legal Arguments Generator v1.0 | Complete Technical Documentation",
        body_style
    ))
    
    # Build PDF
    doc.build(elements)
    
    print(f"✓ PDF Documentation created successfully!")
    print(f"✓ Saved to: {output_path}")
    print(f"✓ File size: {os.path.getsize(output_path) / 1024:.1f} KB")
    
    return output_path


if __name__ == "__main__":
    try:
        pdf_path = create_pdf_documentation()
        print(f"\n✓ Documentation PDF is ready at: {pdf_path}")
    except Exception as e:
        print(f"✗ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
