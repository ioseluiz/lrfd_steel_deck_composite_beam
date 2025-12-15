import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.units import inch

class PDFReportGenerator:
    """
    Genera un reporte PDF detallado con memoria de cálculo paso a paso.
    """
    def __init__(self, filename, data, plot_paths=None):
        self.filename = filename
        self.data = data
        self.plot_paths = plot_paths if plot_paths else {}
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        # Estilos
        self.styles.add(ParagraphStyle(name='HeaderCustom', parent=self.styles['Heading2'], spaceAfter=6, textColor=colors.navy))
        self.styles.add(ParagraphStyle(name='SubHeader', parent=self.styles['Heading3'], spaceAfter=4, textColor=colors.black, fontSize=11))
        self.styles.add(ParagraphStyle(name='CalcStep', parent=self.styles['Normal'], fontName='Courier', fontSize=9, leftIndent=20, spaceAfter=2))
        self.styles.add(ParagraphStyle(name='CalcResult', parent=self.styles['Normal'], fontName='Courier-Bold', fontSize=9, leftIndent=20, spaceAfter=6))

    def generate(self):
        doc = SimpleDocTemplate(self.filename, pagesize=LETTER)
        
        self.elements.append(Paragraph("Memoria de Cálculo: Diseño Viga Compuesta", self.styles['Title']))
        self.elements.append(Spacer(1, 0.2 * inch))

        self._add_input_summary()
        self._add_detailed_calculation_steps()
        self._add_summary_table()
        self._add_plots_section()
        
        try:
            doc.build(self.elements)
            print(f"Reporte generado: {self.filename}")
        except Exception as e:
            print(f"Error PDF: {e}")
            raise e # Re-raise to catch in controller if needed

    def _add_input_summary(self):
        self.elements.append(Paragraph("1. Datos de Entrada", self.styles['HeaderCustom']))
        
        inputs = self.data['inputs']
        beam = inputs['beam_properties']
        
        # Formatear info de conector
        c_type = inputs.get('connector_type', 'Stud')
        c_space = inputs.get('connector_spacing', 12.0)
        c_info = f"{c_type} @ {c_space} in"
        
        # Datos organizados en dos columnas
        data_left = [
            ["Luz (L)", f"{inputs['span_ft']} ft"],
            ["Espaciamiento (S)", f"{inputs['spacing_ft']} ft"],
            ["Perfil Acero", f"{inputs['beam_name']}"],
            ["  - Area (As)", f"{beam['A']} in²"],
            ["  - Inercia (Ix)", f"{beam['Ix']} in⁴"],
            ["  - Peralte (d)", f"{beam['d']} in"]
        ]
        
        data_right = [
            ["Concreto (f'c)", f"{inputs['fc_ksi']} ksi"],
            ["Acero (Fy)", f"{inputs['fy_ksi']} ksi"],
            ["Losa sobre deck (tc)", f"{inputs['slab_thickness']} in"],
            ["Metal Deck", f"Hr={inputs['rib_height']}\", Wr={inputs['rib_width']}\""],
            ["Conectores", c_info],
            ["Cargas (DL / LL)", f"{inputs['dl_psf']} / {inputs['ll_psf']} psf"]
        ]
        
        # Crear tabla contenedora para el layout de inputs
        t_left = Table(data_left, colWidths=[1.2*inch, 1.2*inch])
        t_right = Table(data_right, colWidths=[1.5*inch, 1.2*inch])
        
        style_inputs = TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ])
        
        t_left.setStyle(style_inputs)
        t_right.setStyle(style_inputs)
        
        main_table = Table([[t_left, t_right]], colWidths=[3.5*inch, 3.5*inch])
        self.elements.append(main_table)
        self.elements.append(Spacer(1, 0.25 * inch))

    def _add_detailed_calculation_steps(self):
        """Genera la sección paso a paso con fórmulas"""
        self.elements.append(Paragraph("2. Memoria de Cálculo Detallada", self.styles['HeaderCustom']))
        
        res = self.data['results']
        steps_load = res['loads']['steps']
        steps_conn = res['conn_data']['steps']
        steps_flex = res['strength']['calc_steps']
        
        # Bloque Cargas
        # Usamos KeepTogether para evitar saltos de página a mitad de bloque
        block_cargas = [
            Paragraph("2.1 Análisis de Cargas", self.styles['SubHeader']),
            Paragraph(steps_load['w_u'], self.styles['CalcStep']),
            Paragraph(steps_load['M_u'], self.styles['CalcResult'])
        ]
        self.elements.append(KeepTogether(block_cargas))
        
        # Bloque Conectores
        block_conn = [
            Paragraph("2.2 Capacidad de Conectores (AISC I8)", self.styles['SubHeader']),
            Paragraph(f"Fórmula: {steps_conn['Qn_f']}", self.styles['CalcStep']),
            Paragraph(f"Sustitución: {steps_conn['Qn_s']}", self.styles['CalcStep']),
            Paragraph(f"Qn Unitario: {res['conn_data']['Qn_unit']:.2f} kips", self.styles['CalcResult']),
            
            Paragraph("2.3 Demanda de Cortante Horizontal", self.styles['SubHeader']),
            Paragraph(f"Concreto (0.85 f'c Ac): {steps_conn['Vh_conc']}", self.styles['CalcStep']),
            Paragraph(f"Acero (As Fy): {steps_conn['Vh_steel']}", self.styles['CalcStep']),
            Paragraph(f"Control Vh: {steps_conn['Vh_ctrl']}", self.styles['CalcResult']),
            Paragraph(f"Suma Qn (Proporcionada): {steps_conn['Sum_Qn']}", self.styles['CalcResult'])
        ]
        self.elements.append(KeepTogether(block_conn))
        
        # Bloque Flexión
        block_flex = [
            Paragraph("2.4 Resistencia a Flexión (Eje Neutro Plástico)", self.styles['SubHeader']),
            Paragraph(steps_flex['C_force'], self.styles['CalcStep']),
            Paragraph(f"Bloque 'a': {steps_flex['a']}", self.styles['CalcStep']),
            Paragraph(steps_flex['Y2'], self.styles['CalcStep']),
            Paragraph(steps_flex['arm'], self.styles['CalcStep']),
            Paragraph(steps_flex['Mn'], self.styles['CalcStep']),
            Paragraph(steps_flex['PhiMn'], self.styles['CalcResult'])
        ]
        self.elements.append(KeepTogether(block_flex))
        
        self.elements.append(Spacer(1, 0.1 * inch))

    def _add_summary_table(self):
        # Tabla resumen final (Semaforos)
        self.elements.append(Paragraph("3. Resumen de Verificaciones", self.styles['HeaderCustom']))
        
        # Recuperar datos
        res = self.data['results']
        Mu = res['loads']['M_u']
        PhiMn = res['strength']['phi_Mn']
        ratio = res['strength']['ratio']
        status = res['strength']['status']
        
        # Recalculo rápido para la tabla del PDF
        Vu = res['loads']['V_u']
        # V_n approx
        inputs = self.data['inputs']
        d = inputs['beam_properties']['d']
        tw = inputs['beam_properties']['tw']
        Fy = inputs['fy_ksi']
        PhiVn = 1.0 * 0.6 * Fy * d * tw
        ratio_shear = Vu / PhiVn
        status_shear = "OK" if ratio_shear <= 1.0 else "FALLA"
        
        # Deflexión
        w_serv = res['w_service']
        L_in = inputs['span_ft'] * 12
        I_st = inputs['beam_properties']['Ix']
        delta = (5 * (w_serv/12) * L_in**4)/(384*29000*I_st)
        limit = L_in / 360
        ratio_def = delta/limit
        status_def = "OK" if ratio_def <= 1.0 else "CHECK"
        
        data = [
            ["Verificación", "Demanda", "Capacidad", "Ratio", "Estado"],
            ["Flexión", f"{Mu:.1f} k-ft", f"{PhiMn:.1f} k-ft", f"{ratio:.2f}", status],
            ["Cortante", f"{Vu:.1f} k", f"{PhiVn:.1f} k", f"{ratio_shear:.2f}", status_shear],
            ["Deflexión", f"{delta:.3f} in", f"{limit:.3f} in", f"{ratio_def:.2f}", status_def],
        ]
        
        t = Table(data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 0.8*inch, 1.0*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        
        # Colorear estados
        for i, row in enumerate(data[1:], 1):
            st = row[-1]
            color = colors.green if st == "OK" else (colors.orange if st == "CHECK" else colors.red)
            t.setStyle(TableStyle([('TEXTCOLOR', (-1,i), (-1,i), color), ('FONTNAME', (-1,i), (-1,i), 'Helvetica-Bold')]))

        self.elements.append(t)
        self.elements.append(Spacer(1, 0.2*inch))

    def _add_plots_section(self):
        self.elements.append(Paragraph("4. Gráficos", self.styles['HeaderCustom']))
        if 'moment_plot' in self.plot_paths and os.path.exists(self.plot_paths['moment_plot']):
            im = Image(self.plot_paths['moment_plot'], width=6.5*inch, height=5*inch)
            self.elements.append(im)
            
        if 'section_plot' in self.plot_paths and os.path.exists(self.plot_paths['section_plot']):
            self.elements.append(Paragraph("Detalle de Sección:", self.styles['SubHeader']))
            im = Image(self.plot_paths['section_plot'], width=6*inch, height=4*inch)
            self.elements.append(im)