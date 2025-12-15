import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from models.calculator import CompositeBeamDesign
from models.section_database import SteelSectionDatabase
from utils.report_generator import PDFReportGenerator

class AppController:
    def __init__(self, view):
        self.view = view
        self.db = SteelSectionDatabase.get_sections()
        
        self.view.section_combo.addItems(self.db.keys())
        default_index = self.view.section_combo.findText("W18X35")
        if default_index != -1: self.view.section_combo.setCurrentIndex(default_index)
        
        self.view.calc_btn.clicked.connect(self.run_calculation)
        self.view.export_btn.clicked.connect(self.export_to_pdf)
        self.view.connector_type_combo.currentTextChanged.connect(self.update_connector_ui)
        
        self.last_results = None
        self.last_inputs = None
        
        self.update_connector_ui(self.view.connector_type_combo.currentText())

    def update_connector_ui(self, type_text):
        if type_text == "Stud":
            self.view.stud_params_widget.setVisible(True)
            self.view.channel_params_widget.setVisible(False)
        else:
            self.view.stud_params_widget.setVisible(False)
            self.view.channel_params_widget.setVisible(True)

    def run_calculation(self):
        try:
            selected_beam_name = self.view.section_combo.currentText()
            if selected_beam_name not in self.db:
                QMessageBox.warning(self.view, "Error", "Perfil no válido.")
                return

            beam_props = self.db[selected_beam_name]
            
            inputs = {
                'span_ft': float(self.view.span_input.text()),
                'spacing_ft': float(self.view.spacing_input.text()),
                'slab_thickness': float(self.view.slab_thick_input.text()),
                'fc_ksi': float(self.view.fc_input.text()),
                'fy_ksi': float(self.view.fy_input.text()),
                'dl_psf': float(self.view.dl_input.text()),
                'll_psf': float(self.view.ll_input.text()),
                'rib_height': float(self.view.rib_h_input.text()),
                'rib_width': float(self.view.rib_w_input.text()),
                'beam_properties': beam_props,
                'beam_name': selected_beam_name,
                'deck_orientation': self.view.deck_orient_combo.currentText(),
                'connector_type': self.view.connector_type_combo.currentText(),
                'connector_spacing': float(self.view.conn_spacing_input.text())
            }
            
            props = {}
            if inputs['connector_type'] == 'Stud':
                diam_map = {"1/2": 0.5, "5/8": 0.625, "3/4": 0.75, "7/8": 0.875}
                d_txt = self.view.stud_diam_combo.currentText()
                props['diameter'] = diam_map.get(d_txt, 0.75)
                props['fu'] = float(self.view.stud_fu_input.text())
            else:
                props['tf'] = float(self.view.channel_tf_input.text())
                props['tw'] = float(self.view.channel_tw_input.text())
                props['length'] = float(self.view.channel_len_input.text())
            inputs['connector_props'] = props
            
            model = CompositeBeamDesign(inputs)
            loads = model.calculate_loads()
            conn_data = model.calculate_connectors()
            strength = model.check_composite_strength(loads['M_u'])
            
            s = inputs['spacing_ft']
            w_service = s * (inputs['dl_psf'] + inputs['ll_psf']) / 1000.0
            
            d = beam_props['d']
            tw = beam_props['tw']
            Phi_Vn = 1.0 * 0.6 * inputs['fy_ksi'] * d * tw
            ratio_shear = loads['V_u'] / Phi_Vn
            status_shear = "OK" if ratio_shear <= 1.0 else "FALLA"
            
            L_in = inputs['span_ft'] * 12.0
            I_steel = beam_props['Ix']
            delta = (5 * (w_service/12.0) * (L_in**4)) / (384 * 29000 * I_steel)
            limit_L360 = L_in / 360.0
            ratio_def = delta / limit_L360
            status_def = "OK" if ratio_def <= 1.0 else "CHECK"
            
            self.last_inputs = inputs
            self.last_results = {
                "loads": loads,
                "strength": strength,
                "conn_data": conn_data,
                "w_service": w_service
            }
            
            self.generate_html_report(inputs, loads, strength, conn_data, Phi_Vn, ratio_shear, status_shear, delta, limit_L360, ratio_def, status_def)
            
            # --- ACTUALIZAR GRÁFICOS ---
            # 1. Figuras Steel Tips (NUEVO)
            self.view.steeltips_widget.plot_figures(inputs, self.last_results)
            
            # 2. Diagramas V/M/D
            self.view.diagram_widget.plot_diagrams(inputs['span_ft'], loads['w_u'], w_service, beam_props['Ix'])
            
            # 3. Sección Transversal Simple
            d_steel = beam_props['d']
            hr = inputs['rib_height']
            tc = inputs['slab_thickness']
            pna_bottom = (d_steel + hr + tc) - strength['a']
            self.view.section_widget.draw_section(inputs, pna_bottom)
            
            self.view.export_btn.setEnabled(True)
            self.view.tabs.setCurrentIndex(1) # Cambiar foco a la pestaña de figuras
            
        except ValueError:
            self.view.report_label.setText("<b style='color:red'>Error: Datos numéricos inválidos.</b>")

    # (El método generate_html_report y export_to_pdf se mantienen igual que en versiones anteriores, no es necesario repetirlos aquí si no cambiaron lógica interna)
    def generate_html_report(self, inputs, loads, strength, conn_data, Phi_Vn, ratio_shear, status_shear, delta, limit, ratio_def, status_def):
        # ... (Lógica de reporte HTML igual al snippet anterior)
        # Por brevedad en la respuesta, asumo que este método existe tal cual lo definimos en el paso anterior.
        # Si necesitas el código completo, por favor indícamelo.
        
        # REPETICIÓN DEL MÉTODO PARA INTEGRIDAD DEL BLOQUE DE CÓDIGO
        steps_flex = strength['calc_steps']
        steps_conn = conn_data['steps']
        steps_load = loads['steps']
        status_flex = strength['status']
        c_status = "FULL" if conn_data['is_full_composite'] else "PARCIAL"
        orient = inputs['deck_orientation']
        a_full = strength.get('a_full', 0)
        phiMn_full = strength.get('phi_Mn_full', 0)
        
        html = f"""
        <style>
            h3 {{ color: #003366; margin-bottom: 5px; }}
            h4 {{ background-color: #eee; padding: 5px; border-left: 4px solid #003366; margin-top: 15px; }}
            .step {{ font-family: Consolas, monospace; font-size: 10pt; color: #333; margin-left: 15px; margin-bottom: 3px; }}
            .res {{ font-weight: bold; color: #000; }}
            .ok {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
            .info {{ color: blue; font-style: italic; font-size: 9pt; }}
            hr {{ border: 0; border-top: 1px solid #ccc; }}
        </style>
        <h3>Memoria de Cálculo Detallada (AISC 360-16)</h3>
        <h4>1. Datos Generales</h4>
        <div class="step">Orientación Ribs: <b>{orient}</b></div>
        <div class="step">Concreto en Ribs: {"INCLUIDO" if orient == 'Parallel' else "DESPRECIADO"}</div>
        <h4>2. Análisis de Cargas</h4>
        <div class="step">{steps_load['w_u']}</div>
        <div class="step">{steps_load['M_u']}</div>
        <h4>3. Capacidad de Conectores (Sec. I8)</h4>
        <div class="step">Formula Qn: {steps_conn['Qn_f']}</div>
        <div class="step">Sustitución: {steps_conn['Qn_s']}</div>
        <div class="step res">Capacidad Unitaria Qn = {conn_data['Qn_unit']:.2f} kips</div>
        <div class="step">Conectores (L/2): N = {conn_data['N_half']} und</div>
        <div class="step res">Suma Qn = {steps_conn['Sum_Qn']}</div>
        <h4>4. Demanda de Cortante Horizontal (Vh)</h4>
        <div class="step">Concreto (0.85f'cAc): {steps_conn['Vh_conc']}</div>
        <div class="step">Acero (AsFy): {steps_conn['Vh_steel']}</div>
        <div class="step res">Control Vh = {steps_conn['Vh_ctrl']}</div>
        <div class="step">Acción Compuesta: <b>{c_status}</b> ({strength['percent_composite']:.1f}%)</div>
        <h4>5. Resistencia a Flexión</h4>
        <div class="step">Bloque Compresión a = {strength['a']:.2f} in</div>
        <div class="step res">Diseño Phi*Mn: {steps_flex['PhiMn']}</div>
        <div class="info">Full Composite (Ref): a={a_full:.2f} in | PhiMn={phiMn_full:.1f} k-ft</div>
        <h4>6. Verificación Final</h4>
        <div class="step">Ratio Flexión: <b>{strength['ratio']:.2f}</b> <span class="{'ok' if strength['status']=='OK' else 'fail'}">[{strength['status']}]</span></div>
        <div class="step">Ratio Cortante: <b>{ratio_shear:.2f}</b> <span class="{'ok' if status_shear=='OK' else 'fail'}">[{status_shear}]</span></div>
        <div class="step">Ratio Deflexión: <b>{ratio_def:.2f}</b> <span class="{'ok' if status_def=='OK' else 'fail'}">[{status_def}]</span></div>
        """
        self.view.report_label.setText(html)

    def export_to_pdf(self):
        if not self.last_results: return
        filename, _ = QFileDialog.getSaveFileName(self.view, "Guardar Reporte", "", "PDF Files (*.pdf)")
        if filename:
            try:
                temp_moment = "temp_diagrams.png"
                temp_section = "temp_section.png"
                self.view.diagram_widget.figure.savefig(temp_moment, dpi=150, bbox_inches='tight')
                self.view.section_widget.figure.savefig(temp_section, dpi=150, bbox_inches='tight')
                
                # Opcional: También guardar las figuras Steel Tips si quieres incluirlas en el PDF
                # temp_steeltips = "temp_steeltips.png"
                # self.view.steeltips_widget.figure.savefig(temp_steeltips, dpi=150, bbox_inches='tight')
                
                pdf = PDFReportGenerator(filename, {
                    'inputs': self.last_inputs,
                    'results': self.last_results
                }, {'moment_plot': temp_moment, 'section_plot': temp_section})
                pdf.generate()
                
                if os.path.exists(temp_moment): os.remove(temp_moment)
                if os.path.exists(temp_section): os.remove(temp_section)
                QMessageBox.information(self.view, "Éxito", f"Reporte guardado en {filename}")
            except Exception as e:
                QMessageBox.critical(self.view, "Error", str(e))