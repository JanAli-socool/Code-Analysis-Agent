"""Tests for PDF exporter."""
import tempfile
from pathlib import Path

from pro.reporting.pdf_exporter import PDFExporter, export_to_pdf


class TestPDFExporter:
    def test_exporter_initialization(self):
        exporter = PDFExporter()
        assert exporter.has_reportlab is True
    
    def test_export_simple_report(self):
        exporter = PDFExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.pdf"
            
            data = {
                'repository_path': '/test/repo',
                'analyzed_at': '2024-01-01T00:00:00Z',
                'overall_score': 85.5,
                'risk_level': 'low',
                'category_scores': [
                    {'name': 'complexity', 'score': 90.0, 'weight': 2.0, 'duration_ms': 100, 'findings': []},
                    {'name': 'security', 'score': 80.0, 'weight': 3.0, 'duration_ms': 200, 'findings': []},
                    {'name': 'testing', 'score': 0.0, 'weight': 2.0, 'duration_ms': 50, 'findings': [
                        {'severity': 'high', 'title': 'No tests', 'description': 'No test files found', 'recommendation': 'Add tests'}
                    ]},
                ],
                'summary': 'Good code quality with testing gaps.',
                'strengths': ['Low complexity', 'Good security'],
                'weaknesses': ['No tests'],
                'files_analyzed': 10,
                'total_lines': 500,
                'total_duration_ms': 350,
                'findings': [
                    {'severity': 'high', 'title': 'No tests', 'description': 'No test files found', 'recommendation': 'Add tests', 'file_path': None}
                ]
            }
            
            result = export_to_pdf(data, str(output))
            
            assert result is True
            assert output.exists()
            assert output.stat().st_size > 1000  # At least 1KB
    
    def test_export_with_findings(self):
        exporter = PDFExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.pdf"
            
            data = {
                'repository_path': '/test/repo',
                'analyzed_at': '2024-01-01T00:00:00Z',
                'overall_score': 60.0,
                'risk_level': 'medium',
                'category_scores': [
                    {'name': 'security', 'score': 40.0, 'weight': 3.0, 'duration_ms': 200, 'findings': [
                        {'severity': 'critical', 'title': 'SQL Injection', 'description': 'SQL injection vulnerability', 'recommendation': 'Use parameterized queries', 'file_path': 'main.py', 'line_start': 10},
                        {'severity': 'high', 'title': 'Hardcoded Secret', 'description': 'API key in code', 'recommendation': 'Use env vars', 'file_path': 'config.py', 'line_start': 5},
                    ]},
                ],
                'summary': 'Security issues found.',
                'strengths': [],
                'weaknesses': ['Critical security issues'],
                'files_analyzed': 5,
                'total_lines': 200,
                'total_duration_ms': 200,
                'findings': [
                    {'severity': 'critical', 'title': 'SQL Injection', 'description': 'SQL injection vulnerability', 'recommendation': 'Use parameterized queries', 'file_path': 'main.py', 'line_start': 10},
                    {'severity': 'high', 'title': 'Hardcoded Secret', 'description': 'API key in code', 'recommendation': 'Use env vars', 'file_path': 'config.py', 'line_start': 5},
                ]
            }
            
            result = export_to_pdf(data, str(output))
            
            assert result is True
            assert output.exists()
            assert output.stat().st_size > 1000
    
    def test_risk_colors(self):
        exporter = PDFExporter()
        
        assert exporter._get_risk_color('critical') == exporter.red
        assert exporter._get_risk_color('high') == exporter.orange
        assert exporter._get_risk_color('medium') == exporter.yellow
        assert exporter._get_risk_color('low') == exporter.green
        assert exporter._get_risk_color('unknown') == exporter.black
    
    def test_status_mapping(self):
        exporter = PDFExporter()
        
        assert exporter._get_status(90) == 'PASS'
        assert exporter._get_status(70) == 'WARN'
        assert exporter._get_status(40) == 'FAIL'
    
    def test_severity_colors(self):
        exporter = PDFExporter()
        
        assert exporter._get_severity_color('CRITICAL') == exporter.red
        assert exporter._get_severity_color('HIGH') == exporter.orange
        assert exporter._get_severity_color('MEDIUM') == exporter.yellow
        assert exporter._get_severity_color('LOW') == exporter.green