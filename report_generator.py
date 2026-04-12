from fpdf import FPDF
import datetime

class DossierExporter(FPDF):
    def header(self):
        # Top Secret Banner
        self.set_fill_color(20, 20, 25)
        self.rect(0, 0, 210, 30, 'F')
        
        self.set_font('Courier', 'B', 16)
        self.set_text_color(255, 71, 108) # Red alert color
        self.cell(0, 10, 'CONFIDENTIAL // RECONSPHERE INTELLIGENCE REPORT', 0, 1, 'C')
        
        self.set_font('Courier', 'I', 10)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'GENERATED: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Courier', 'I', 8)
        self.set_text_color(71, 85, 105)
        self.cell(0, 10, f'Page {self.page_no()} // FOR INTERNAL USE ONLY', 0, 0, 'C')

    def add_identity_section(self, identity):
        self.set_font('Courier', 'B', 14)
        self.set_text_color(0, 229, 255) # Cyan header
        self.cell(0, 10, f'> SUBJECT: {identity.get("name", "Unknown").upper()}', 0, 1)
        
        self.set_font('Courier', '', 10)
        self.set_text_color(248, 250, 252)
        self.cell(0, 8, f'  CLASSIFICATION: {identity.get("type", "Unverified")}', 0, 1)
        self.cell(0, 8, f'  INTEL SOURCE:   {identity.get("source", "N/A")}', 0, 1)
        
        if identity.get("github"):
            self.set_text_color(191, 149, 255)
            self.cell(0, 8, f'  GITHUB FOOTPRINT: {identity["github"]}', 0, 1)
        
        self.ln(5)
        self.set_font('Courier', 'I', 10)
        self.set_text_color(148, 163, 184)
        self.multi_cell(0, 6, f'  {identity.get("description", "No additional metadata found.")}')
        self.ln(10)

    def add_neural_section(self, signature):
        if not signature: return
        
        self.set_font('Courier', 'B', 14)
        self.set_text_color(175, 136, 255) # Purple header
        self.cell(0, 10, '> NEURAL BIOMETRIC SIGNATURE', 0, 1)
        
        self.set_font('Courier', '', 10)
        self.set_text_color(248, 250, 252)
        self.cell(0, 8, f'  SIGNATURE ID:     {signature.get("signature_id", "N/A")}', 0, 1)
        self.cell(0, 8, f'  IDENTITY SCORE:   {signature.get("nis_score", 0)}%', 0, 1)
        self.cell(0, 8, f'  BIOMETRIC STATUS: {signature.get("biometric_status", "N/A")}', 0, 1)
        
        self.ln(5)
        self.set_font('Courier', 'I', 9)
        self.set_text_color(148, 163, 184)
        telemetry = signature.get("telemetry", {})
        self.cell(0, 6, f'  TELEMETRY: [Energy: {telemetry.get("energy")}] [Entropy: {telemetry.get("entropy")}]', 0, 1)
        self.ln(10)

def generate_pdf_report(identity, signature):
    pdf = DossierExporter()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Dark background color for the whole page
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 30, 210, 267, 'F')
    
    pdf.add_identity_section(identity)
    pdf.add_neural_section(signature)
    
    return pdf.output()
