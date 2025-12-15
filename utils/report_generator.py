import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.units import inch

class PDFReportGenerator:
    def __init__(self, filename, data, plot_paths=None):
        self.filename = filename
        self.data = data
        self.plot_paths = plot_paths if plot_paths else {}
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        self.styles.add(ParagraphStyle(name='HeaderCustom', parent=self.styles['Heading2'], spaceAfter=6, textColor=colors.navy, borderBottomColor=colors.navy, borderBottomWidth=1, borderPadding=2))
        self.styles.add(ParagraphStyle(name='SubHeader', parent=self.styles['Heading3'], spaceAfter=4, textColor=colors.black, fontSize=11))
        self.styles.add(ParagraphStyle(name='CalcStep', parent=self.styles['Normal'], fontName='Courier', fontSize=9, leftIndent=12, spaceAfter=2))
        self.styles.add(ParagraphStyle(name='CalcResult', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leftIndent=12, spaceAfter=6))

    def generate(self):
        doc = SimpleDocTemplate(self.filename, pagesize=LETTER)
        self.elements.append(Paragraph("Memoria de Cálculo: Viga Compuesta LRFD (AISC 360-16)", self.styles['Title']))
        self.elements.append(Spacer(1, 0.2 * inch))

        self._add_inputs()
        self._add_calcs()
        self._add_shear_calcs() # NUEVA SECCIÓN
        self._add_deflections()
        self._add_plots()
        
        doc.build(self.elements)

    def _add_inputs(self):
        self.elements.append(Paragraph("1. Datos de Entrada", self.styles['HeaderCustom']))
        inp = self.data['inputs']
        beam = inp['beam_properties']
        
        data = [
            ["Luz", f"{inp['span_ft']} ft", "f'c", f"{inp['fc_ksi']} ksi"],
            ["Espaciamiento", f"{inp['spacing_ft']} ft", "Fy", f"{inp['fy_ksi']} ksi"],
            ["Perfil", inp['beam_name'], "Losa (tc)", f"{inp['slab_thickness']} in"],
            ["Cargas (DL/LL)", f"{inp['dl_psf']} / {inp['ll_psf']} psf", "Deck", f"{inp['rib_height']}\" x {inp['rib_width']}\""],
        ]
        t = Table(data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke)]))
        self.elements.append(t)
        self.elements.append(Spacer(1, 0.15*inch))

    def _add_calcs(self):
        res = self.data['results']
        
        # Ancho Efectivo
        self.elements.append(Paragraph("2. Geometría (AISC I3.1a)", self.styles['HeaderCustom']))
        for k, v in res['b_eff_steps'].items():
            self.elements.append(Paragraph(v, self.styles['CalcStep']))
            
        # Conectores
        self.elements.append(Paragraph("3. Conectores (AISC I8)", self.styles['HeaderCustom']))
        c_steps = res['conn_data']['steps']
        self.elements.append(Paragraph(f"Qn: {c_steps['Qn_desc']} = {res['conn_data']['Qn_unit']:.2f} k", self.styles['CalcResult']))
        self.elements.append(Paragraph(c_steps['N_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(c_steps['Vh_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(f"Acción Compuesta: {res['conn_data']['percent']:.1f}%", self.styles['CalcResult']))
        
        # Flexión
        self.elements.append(Paragraph("4. Capacidad a Flexión (AISC I3.2)", self.styles['HeaderCustom']))
        f_steps = res['strength']['steps']
        self.elements.append(Paragraph(f_steps['C_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(f_steps['a_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(f_steps['Y_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(f"Diseño PhiMn: {res['strength']['phi_Mn']:.1f} k-ft (Ratio: {res['strength']['ratio']:.2f})", self.styles['CalcResult']))

    def _add_shear_calcs(self):
        # NUEVA SECCIÓN DE CORTANTE EN PDF
        self.elements.append(Paragraph("5. Cortante (AISC G2)", self.styles['HeaderCustom']))
        shear = self.data['results']['shear']
        steps = shear['steps']
        
        self.elements.append(Paragraph(steps['Aw_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(steps['Formula'], self.styles['CalcStep']))
        self.elements.append(Paragraph(steps['Vn_calc'], self.styles['CalcStep']))
        self.elements.append(Paragraph(f"{steps['PhiVn_calc']} (Ratio: {shear['ratio']:.2f})", self.styles['CalcResult']))

    def _create_trans_table(self, d_dict):
        d = d_dict['table_data']
        beam_name = self.data['inputs']['beam_name']
        data = [
            ["Comp.", "Area", "y", "Ay", "Io", "Ad²"],
            [beam_name, f"{d['steel']['A']:.2f}", f"{d['steel']['y']:.2f}", f"{d['steel']['Ay']:.1f}", f"{d['steel']['Io']:.1f}", f"{d['steel']['Ad2']:.1f}"],
            ["Conc", f"{d['conc']['A']:.2f}", f"{d['conc']['y']:.2f}", f"{d['conc']['Ay']:.1f}", f"{d['conc']['Io']:.1f}", f"{d['conc']['Ad2']:.1f}"],
            ["SUMA", f"{d['sum']['A']:.2f}", "-", f"{d['sum']['Ay']:.1f}", "-", "-"]
        ]
        t = Table(data, colWidths=[0.8*inch]*6)
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.whitesmoke)
        ]))
        return t

    def _add_deflections(self):
        self.elements.append(Paragraph("6. Deflexiones (AISC I3.2)", self.styles['HeaderCustom']))
        res = self.data['results']
        defs = res['deflections']
        Ec = res['conn_data']['Ec']
        n_base = defs['short']['data']['n_base']
        fc_psi = self.data['inputs']['fc_ksi'] * 1000
        
        self.elements.append(Paragraph(f"Ec = 57000 * sqrt({fc_psi:.0f}) / 1000 = {Ec:.1f} ksi", self.styles['CalcStep']))
        self.elements.append(Paragraph(f"n = Es / Ec = 29000 / {Ec:.1f} = {n_base:.2f}", self.styles['CalcStep']))
        self.elements.append(Spacer(1, 0.1*inch))
        
        # Corto Plazo
        self.elements.append(Paragraph(f"A. Corto Plazo (n={defs['short']['data']['n']:.2f})", self.styles['SubHeader']))
        b_tr = defs['short']['data']['b_tr']
        self.elements.append(Paragraph(f"Ancho Equiv. (btr) = beff / n = {b_tr:.2f} in", self.styles['CalcStep']))
        self.elements.append(self._create_trans_table(defs['short']['data']))
        self.elements.append(Paragraph(f"Ieff = {defs['short']['data']['I_eff']:.1f} in⁴ -> Def = {defs['short']['delta']:.3f} in", self.styles['CalcResult']))
        self.elements.append(Spacer(1, 0.1*inch))
        
        # Largo Plazo
        self.elements.append(Paragraph(f"B. Largo Plazo (n={defs['long']['data']['n']:.2f})", self.styles['SubHeader']))
        b_tr_long = defs['long']['data']['b_tr']
        self.elements.append(Paragraph(f"Ancho Equiv. (btr) = beff / n = {b_tr_long:.2f} in", self.styles['CalcStep']))
        self.elements.append(self._create_trans_table(defs['long']['data']))
        self.elements.append(Paragraph(f"Ieff = {defs['long']['data']['I_eff']:.1f} in⁴ -> Def = {defs['long']['delta']:.3f} in", self.styles['CalcResult']))

    def _add_plots(self):
        self.elements.append(Paragraph("7. Gráficos", self.styles['HeaderCustom']))
        if 'moment_plot' in self.plot_paths and os.path.exists(self.plot_paths['moment_plot']):
            self.elements.append(Image(self.plot_paths['moment_plot'], width=6*inch, height=4.5*inch))