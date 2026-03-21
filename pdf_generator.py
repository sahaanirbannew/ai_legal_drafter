# PDF generation functions for legal argument output

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def create_pdf(text, path):

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(path)

    story = []

    for line in text.split("\n"):
        story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)