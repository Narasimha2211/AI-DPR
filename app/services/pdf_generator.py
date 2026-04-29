import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy.orm import Session

from config.postgres_config import SessionLocal
from app.models.postgres_models import DPRDocument, DPRAnalysis, QualityScore, RiskAssessment


def generate_dpr_pdf(document_id: int) -> bytes:
    """Generate a formatted PDF report for a given document.
    
    Synchronous function — uses its own DB session.
    """
    db: Session = SessionLocal()
    try:
        doc_data = db.query(DPRDocument).filter_by(id=document_id).first()
        if not doc_data:
            raise ValueError("Document not found")

        # Eagerly load related records
        analysis = db.query(DPRAnalysis).filter_by(document_id=document_id).first()
        quality = db.query(QualityScore).filter_by(document_id=document_id).first()
        risk = db.query(RiskAssessment).filter_by(document_id=document_id).first()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        h1_style = styles['Heading1']
        h2_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Title
        story.append(Paragraph("DPR AI Evaluation Report", title_style))
        story.append(Spacer(1, 12))
        
        # Meta Information
        upload_date = str(doc_data.upload_date)[:10] if doc_data.upload_date else 'Unknown'
        meta_data = [
            ["Document Name:", getattr(doc_data, 'filename', 'Unknown') or 'Unknown'],
            ["State:", getattr(doc_data, 'state_name', 'Unknown') or 'Unknown'],
            ["Project Type:", getattr(doc_data, 'project_type', 'Unknown') or 'Unknown'],
            ["Date Uploaded:", upload_date],
            ["Project Cost (Cr):", str(getattr(doc_data, 'project_cost_crores', 0) or 0)]
        ]
        meta_table = Table(meta_data, colWidths=[150, 300])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#334155'))
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 24))
        
        # Quality Score Section
        story.append(Paragraph("Quality Assessment", h1_style))
        if quality:
            q_data = [
                ["Overall Grade", f"{getattr(quality, 'grade', '-')} ({getattr(quality, 'composite_score', 0):.1f}/100)"],
                ["Section Completeness", f"{getattr(quality, 'section_completeness_score', 0):.1f}/25"],
                ["Technical Depth", f"{getattr(quality, 'technical_depth_score', 0):.1f}/20"],
                ["Financial Accuracy", f"{getattr(quality, 'financial_accuracy_score', 0):.1f}/20"],
                ["Compliance", f"{getattr(quality, 'compliance_score', 0):.1f}/20"],
                ["Risk Assessment", f"{getattr(quality, 'risk_assessment_quality_score', 0):.1f}/15"]
            ]
            q_table = Table(q_data, colWidths=[200, 200])
            q_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(q_table)
        else:
            story.append(Paragraph("No quality assessment data available.", normal_style))
        story.append(Spacer(1, 24))

        # Risk Assessment Section
        story.append(Paragraph("Risk Predictor", h1_style))
        if risk:
            r_data = [
                ["Overall Risk Level", getattr(risk, 'overall_risk_level', 'Unknown')],
                ["Cost Overrun Probability", f"{(getattr(risk, 'cost_overrun_probability', 0) * 100):.1f}%"],
                ["Schedule Delay Probability", f"{(getattr(risk, 'delay_probability', 0) * 100):.1f}%"],
            ]
            r_table = Table(r_data, colWidths=[200, 200])
            r_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(r_table)
        else:
            story.append(Paragraph("No risk assessment data available.", normal_style))
        story.append(Spacer(1, 24))

        # NLP Analysis Notes
        story.append(Paragraph("Automated Insights", h1_style))
        if analysis:
            story.append(Paragraph(f"Extracted {getattr(analysis, 'sections_found', 0)} out of {getattr(analysis, 'sections_total', 14)} standard DPR sections.", normal_style))
            story.append(Spacer(1, 12))
            story.append(Paragraph("Key Entities Found:", h2_style))
            orgs = getattr(analysis, 'organizations_count', 0)
            locs = getattr(analysis, 'locations_count', 0)
            story.append(Paragraph(f"- Organizations identified: {orgs}", normal_style))
            story.append(Paragraph(f"- Locations identified: {locs}", normal_style))
        else:
            story.append(Paragraph("No NLP analysis data available.", normal_style))
            
        doc.build(story)
        return buffer.getvalue()
    finally:
        db.close()
