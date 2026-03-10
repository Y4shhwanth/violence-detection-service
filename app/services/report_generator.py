"""PDF report generator using fpdf2."""
import os
import tempfile
from typing import Dict, Any, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates PDF reports from analysis results."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def generate(self, result: Dict[str, Any], job_id: str) -> str:
        """Generate a PDF report and return the file path."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 12, 'Violence Detection Analysis Report', ln=True, align='C')
        pdf.ln(5)

        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Job ID: {job_id}', ln=True)
        pdf.ln(5)

        # Summary
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Summary', ln=True)
        pdf.set_font('Helvetica', '', 11)

        decision = result.get('final_decision', 'Unknown')
        confidence = result.get('confidence', 0)
        pdf.cell(0, 7, f'Decision: {decision}', ln=True)
        pdf.cell(0, 7, f'Confidence: {confidence:.1f}%', ln=True)
        pdf.cell(0, 7, f'Message: {result.get("message", "")}', ln=True)

        severity = result.get('severity', {})
        if severity:
            pdf.cell(0, 7, f'Severity: {severity.get("severity_label", "N/A")} ({severity.get("severity_score", 0):.0f})', ln=True)
        pdf.ln(5)

        # Modality Breakdown
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Modality Breakdown', ln=True)
        pdf.set_font('Helvetica', '', 11)

        for modality in ['video', 'audio', 'text']:
            pred = result.get(f'{modality}_prediction')
            if pred and pred.get('class') != 'Error':
                cls = pred.get('class', 'N/A')
                conf = pred.get('confidence', 0)
                pdf.cell(0, 7, f'{modality.capitalize()}: {cls} ({conf:.1f}%)', ln=True)
        pdf.ln(5)

        # Violations
        violations = result.get('violations', [])
        if violations:
            pdf.set_font('Helvetica', 'B', 14)
            pdf.cell(0, 10, f'Violations ({len(violations)})', ln=True)
            pdf.set_font('Helvetica', '', 10)

            for v in violations[:10]:
                mod = v.get('modality', '?')
                start = v.get('start_time', v.get('sentence_index', '?'))
                end = v.get('end_time', '')
                reason = v.get('reason', v.get('sentence', ''))[:80]
                line = f'[{mod}] {start}'
                if end:
                    line += f'-{end}'
                line += f': {reason}'
                pdf.cell(0, 6, line, ln=True)
            pdf.ln(5)

        # Policy Matches
        policy = result.get('policy_matches', {})
        matched = policy.get('matched_policies', [])
        if matched:
            pdf.set_font('Helvetica', 'B', 14)
            pdf.cell(0, 10, 'Policy Matches', ln=True)
            pdf.set_font('Helvetica', '', 10)

            for m in matched[:5]:
                pdf.cell(0, 6, f'{m.get("section", "")}: {m.get("title", "")}', ln=True)
            pdf.cell(0, 7, f'Recommended severity: {policy.get("recommended_severity", "N/A")}', ln=True)

        # Save
        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        pdf.output(path)
        return path


_report_generator = None


def get_report_generator() -> ReportGenerator:
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator
