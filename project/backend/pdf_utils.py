import os
import uuid
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

def generate_chat_pdf(messages: List[Dict[str, Any]], session_id: str) -> str:
    """
    Generates a PDF from a list of chat history messages.
    Returns the file path of the generated PDF.
    """
    filename = f"chat_export_{session_id}_{uuid.uuid4().hex[:6]}.pdf"
    output_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterTitle', alignment=TA_CENTER, fontSize=16, spaceAfter=20, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='UserMsg', textColor="blue", spaceAfter=5, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='AssistantMsg', textColor="black", spaceAfter=15, fontName="Helvetica"))

    Story = []
    
    Story.append(Paragraph(f"INGRES AI - Chat Transcript", styles["CenterTitle"]))
    Story.append(Spacer(1, 12))
    
    for msg in messages:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        
        if role.lower() == "user":
            Story.append(Paragraph(f"You:", styles["UserMsg"]))
            # Simple text conversion for PDF
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    Story.append(Paragraph(line, styles["AssistantMsg"]))
        else:
            Story.append(Paragraph(f"INGRES AI:", styles["UserMsg"]))
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    Story.append(Paragraph(line, styles["AssistantMsg"]))
            
            citations = msg.get("citations", [])
            if citations:
                Story.append(Paragraph(f"Citations: {', '.join(citations)}", styles["AssistantMsg"]))
        
    doc.build(Story)
    return filepath
