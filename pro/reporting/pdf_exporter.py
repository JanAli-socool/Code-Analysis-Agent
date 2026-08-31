"""PDF Export for analysis reports."""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReportData:
    repository_path: str
    analyzed_at: str
    overall_score: float
    risk_level: str
    category_scores: List[Dict[str, Any]]
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    files_analyzed: int
    total_lines: int
    total_duration_ms: float
    findings: List[Dict[str, Any]]


class PDFExporter:
    def __init__(self):
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.colors import HexColor, black, white, red, orange, yellow, green
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.platypus.flowables import KeepTogether
            
            self.has_reportlab = True
            self.letter = letter
            self.A4 = A4
            self.getSampleStyleSheet = getSampleStyleSheet
            self.ParagraphStyle = ParagraphStyle
            self.inch = inch
            self.HexColor = HexColor
            self.black = black
            self.white = white
            self.red = red
            self.orange = orange
            self.yellow = yellow
            self.green = green
            self.SimpleDocTemplate = SimpleDocTemplate
            self.Paragraph = Paragraph
            self.Spacer = Spacer
            self.Table = Table
            self.TableStyle = TableStyle
            self.PageBreak = PageBreak
            self.HRFlowable = HRFlowable
            self.TA_CENTER = TA_CENTER
            self.TA_LEFT = TA_LEFT
            self.TA_RIGHT = TA_RIGHT
            self.KeepTogether = KeepTogether
        except ImportError:
            self.has_reportlab = False
    
    def export(self, data: ReportData, output_path: str) -> bool:
        """Export analysis report to PDF."""
        if not self.has_reportlab:
            raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")
        
        doc = self.SimpleDocTemplate(
            output_path,
            pagesize=self.A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = self.getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = self.ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=self.HexColor('#1a1a2e'),
            spaceAfter=6,
            alignment=self.TA_CENTER
        )
        
        subtitle_style = self.ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=self.HexColor('#16213e'),
            spaceAfter=4,
            alignment=self.TA_CENTER
        )
        
        heading_style = self.ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=self.HexColor('#0f3460'),
            spaceBefore=16,
            spaceAfter=8,
            borderWidth=0,
            borderPadding=0,
        )
        
        subheading_style = self.ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=self.HexColor('#16213e'),
            spaceBefore=10,
            spaceAfter=6,
        )
        
        body_style = self.ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=6,
        )
        
        bullet_style = self.ParagraphStyle(
            'CustomBullet',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=3,
        )
        
        # Title page
        story.append(self.Spacer(1, 2*self.inch))
        story.append(self.Paragraph("Code Analysis Report", title_style))
        story.append(self.Spacer(1, 0.3*self.inch))
        story.append(self.Paragraph(f"Repository: {Path(data.repository_path).name}", subtitle_style))
        story.append(self.Spacer(1, 0.2*self.inch))
        story.append(self.Paragraph(f"Analyzed: {data.analyzed_at}", styles['Normal']))
        story.append(self.PageBreak())
        
        # Executive Summary
        story.append(self.Paragraph("Executive Summary", heading_style))
        story.append(self.HRFlowable(width="100%", thickness=2, color=self.HexColor('#0f3460')))
        story.append(self.Spacer(1, 0.1*self.inch))
        
        # Score box
        risk_color = self._get_risk_color(data.risk_level)
        score_data = [
            ['Overall Score', f"{data.overall_score:.1f}/100"],
            ['Risk Level', data.risk_level.upper()],
            ['Files Analyzed', str(data.files_analyzed)],
            ['Total Lines', str(data.total_lines)],
            ['Analysis Duration', f"{data.total_duration_ms:.0f}ms"],
        ]
        
        score_table = self.Table(score_data, colWidths=[2.5*self.inch, 3*self.inch])
        score_table.setStyle(self.TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HexColor('#0f3460')),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, self.HexColor('#ddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.white, self.HexColor('#f5f5f5')]),
        ]))
        story.append(score_table)
        story.append(self.Spacer(1, 0.2*self.inch))
        
        # Risk level indicator
        risk_text = f"<b>Risk Assessment:</b> {data.risk_level.upper()}"
        risk_para = self.Paragraph(risk_text, self.ParagraphStyle('Risk', parent=body_style, textColor=risk_color, fontSize=12))
        story.append(risk_para)
        story.append(self.Spacer(1, 0.2*self.inch))
        
        # Summary
        story.append(self.Paragraph("Summary", subheading_style))
        story.append(self.Paragraph(data.summary, body_style))
        story.append(self.Spacer(1, 0.2*self.inch))
        
        # Strengths
        if data.strengths:
            story.append(self.Paragraph("Strengths", subheading_style))
            for strength in data.strengths:
                story.append(self.Paragraph(f"✓ {strength}", bullet_style))
            story.append(self.Spacer(1, 0.1*self.inch))
        
        # Weaknesses
        if data.weaknesses:
            story.append(self.Paragraph("Weaknesses", subheading_style))
            for weakness in data.weaknesses:
                story.append(self.Paragraph(f"✗ {weakness}", bullet_style))
            story.append(self.Spacer(1, 0.1*self.inch))
        
        story.append(self.PageBreak())
        
        # Category Scores
        story.append(self.Paragraph("Category Scores", heading_style))
        story.append(self.HRFlowable(width="100%", thickness=2, color=self.HexColor('#0f3460')))
        story.append(self.Spacer(1, 0.1*self.inch))
        
        cat_data = [['Category', 'Score', 'Weight', 'Status', 'Duration']]
        for cat in data.category_scores:
            status = self._get_status(cat['score'])
            status_color = self._get_status_color(cat['score'])
            cat_data.append([
                cat['name'].replace('_', ' ').title(),
                f"{cat['score']:.1f}/100",
                f"{cat['weight']}x",
                status,
                f"{cat['duration_ms']:.0f}ms"
            ])
        
        cat_table = self.Table(cat_data, colWidths=[2*self.inch, 1*self.inch, 0.7*self.inch, 1*self.inch, 1*self.inch])
        cat_table.setStyle(self.TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HexColor('#0f3460')),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, self.HexColor('#ddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.white, self.HexColor('#f5f5f5')]),
        ]))
        story.append(cat_table)
        story.append(self.Spacer(1, 0.2*self.inch))
        
        # Top Findings
        if data.findings:
            story.append(self.PageBreak())
            story.append(self.Paragraph("Top Findings", heading_style))
            story.append(self.HRFlowable(width="100%", thickness=2, color=self.HexColor('#0f3460')))
            story.append(self.Spacer(1, 0.1*self.inch))
            
            # Sort by severity
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            sorted_findings = sorted(
                data.findings, 
                key=lambda f: severity_order.get(f.get('severity', '').lower(), 4)
            )[:20]  # Top 20
            
            for finding in sorted_findings:
                severity = finding.get('severity', '').upper()
                severity_color = self._get_severity_color(severity)
                
                finding_text = f"<b>[{severity}]</b> {finding.get('title', 'Unknown')}"
                if finding.get('file_path'):
                    finding_text += f" (<i>{finding['file_path']}"
                    if finding.get('line_start'):
                        finding_text += f":{finding['line_start']}"
                    finding_text += "</i>)"
                
                p = self.Paragraph(finding_text, self.ParagraphStyle('Finding', parent=body_style, textColor=severity_color))
                story.append(p)
                
                if finding.get('description'):
                    desc = self.Paragraph(finding['description'], self.ParagraphStyle('Desc', parent=body_style, leftIndent=20, fontSize=9, textColor=self.HexColor('#555')))
                    story.append(desc)
                
                if finding.get('recommendation'):
                    rec = self.Paragraph(f"<b>Recommendation:</b> {finding['recommendation']}", self.ParagraphStyle('Rec', parent=body_style, leftIndent=20, fontSize=9, textColor=self.HexColor('#0f3460')))
                    story.append(rec)
                
                story.append(self.Spacer(1, 0.1*self.inch))
        
        # Footer
        story.append(self.Spacer(1, 0.5*self.inch))
        story.append(self.HRFlowable(width="100%", thickness=1, color=self.HexColor('#ddd')))
        story.append(self.Paragraph(
            f"Generated by Code Analysis Agent v1.0.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=self.HexColor('#999'), alignment=self.TA_CENTER)
        ))
        
        doc.build(story)
        return True
    
    def _get_risk_color(self, risk_level: str):
        colors = {
            'critical': self.red,
            'high': self.orange,
            'medium': self.yellow,
            'low': self.green,
        }
        return colors.get(risk_level.lower(), self.black)
    
    def _get_status(self, score: float) -> str:
        if score >= 80:
            return "PASS"
        elif score >= 60:
            return "WARN"
        else:
            return "FAIL"
    
    def _get_status_color(self, score: float):
        if score >= 80:
            return self.green
        elif score >= 60:
            return self.orange
        else:
            return self.red
    
    def _get_severity_color(self, severity: str):
        colors = {
            'CRITICAL': self.red,
            'HIGH': self.orange,
            'MEDIUM': self.yellow,
            'LOW': self.green,
        }
        return colors.get(severity, self.black)


def export_to_pdf(analysis_result: Dict[str, Any], output_path: str) -> bool:
    """Convenience function to export analysis result to PDF."""
    exporter = PDFExporter()
    
    # Flatten findings from all categories
    all_findings = []
    for cat in analysis_result.get('category_scores', []):
        for f in cat.get('findings', []):
            f_copy = f.copy()
            f_copy['category'] = cat['name']
            all_findings.append(f_copy)
    
    data = ReportData(
        repository_path=analysis_result.get('repository_path', ''),
        analyzed_at=analysis_result.get('analyzed_at', ''),
        overall_score=analysis_result.get('overall_score', 0),
        risk_level=analysis_result.get('risk_level', 'unknown'),
        category_scores=analysis_result.get('category_scores', []),
        summary=analysis_result.get('summary', ''),
        strengths=analysis_result.get('strengths', []),
        weaknesses=analysis_result.get('weaknesses', []),
        files_analyzed=analysis_result.get('files_analyzed', 0),
        total_lines=analysis_result.get('total_lines', 0),
        total_duration_ms=analysis_result.get('total_duration_ms', 0),
        findings=all_findings
    )
    
    return exporter.export(data, output_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python pdf_exporter.py <analysis_json> <output_pdf>")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        data = json.load(f)
    
    export_to_pdf(data, sys.argv[2])
    print(f"PDF exported to {sys.argv[2]}")