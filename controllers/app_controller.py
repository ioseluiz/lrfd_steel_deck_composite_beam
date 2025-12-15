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
            
            # --- MODELO ---
            model = CompositeBeamDesign(inputs)
            loads = model.calculate_loads()
            b_eff, b_eff_steps = model.get_effective_width()
            conn_data = model.calculate_connectors()
            strength = model.check_composite_strength(loads['M_u'], conn_data)
            
            # NUEVO: Cálculo detallado de cortante
            shear = model.check_shear_strength(loads['V_u'])
            
            deflections = model.calculate_deflections(conn_data, loads)
            
            pna_bottom = (beam_props['d'] + inputs['rib_height'] + inputs['slab_thickness']) - strength['a']
            
            self.last_inputs = inputs
            self.last_results = {
                "loads": loads,
                "b_eff_steps": b_eff_steps,
                "strength": strength,
                "conn_data": conn_data,
                "deflections": deflections,
                "w_service": loads['w_service'],
                "shear": shear # Estructura completa ahora
            }
            
            self.generate_html_report(self.last_results, inputs)
            
            self.view.steeltips_widget.plot_figures(inputs, self.last_results)
            self.view.diagram_widget.plot_diagrams(inputs['span_ft'], loads['w_u'], loads['w_service'], beam_props['Ix'])
            self.view.section_widget.draw_section(inputs, pna_bottom)
            
            self.view.export_btn.setEnabled(True)
            self.view.tabs.setCurrentIndex(0)
            
        except ValueError:
            self.view.report_label.setText("<b style='color:red'>Error: Datos numéricos inválidos.</b>")
        except Exception as e:
            self.view.report_label.setText(f"<b style='color:red'>Error Crítico: {str(e)}</b>")

    def generate_html_report(self, res, inputs):
        l_steps = res['loads']['steps']
        c_steps = res['conn_data']['steps']
        f_steps = res['strength']['steps']
        s_steps = res['shear']['steps'] # Steps de cortante
        b_steps = res['b_eff_steps']
        
        conn = res['conn_data']
        st = res['strength']
        defs = res['deflections']
        shear = res['shear']
        beam_name = inputs['beam_name']
        b_eff = st['b_eff']
        
        Ec = conn['Ec']
        n_base = defs['short']['data']['n_base']
        fc_psi = inputs['fc_ksi'] * 1000
        
        css = """
        <style>
            h3 { color: #004488; border-bottom: 2px solid #004488; margin-bottom: 5px; }
            h4 { background-color: #f2f2f2; padding: 5px; border-left: 5px solid #004488; margin-top: 10px; font-weight: bold;}
            .step { font-family: monospace; font-size: 10pt; margin-left: 10px; color: #333; }
            .result { font-weight: bold; margin-left: 10px; margin-bottom: 3px; color: #000; }
            table { width: 100%; border-collapse: collapse; font-size: 9pt; margin-top: 5px; }
            th { background-color: #004488; color: white; padding: 4px; text-align: center; }
            td { border: 1px solid #ddd; padding: 3px; text-align: center; }
            .pass { color: green; font-weight: bold; }
            .fail { color: red; font-weight: bold; }
        </style>
        """
        
        def mk_tbl(d): 
            dd = d['table_data']
            return f"""
            <table>
            <tr><th>Item</th><th>A (in²)</th><th>y (in)</th><th>Ay (in³)</th><th>Io (in⁴)</th><th>Ad² (in⁴)</th></tr>
            <tr><td><b>{beam_name}</b></td><td>{dd['steel']['A']:.2f}</td><td>{dd['steel']['y']:.2f}</td><td>{dd['steel']['Ay']:.1f}</td><td>{dd['steel']['Io']:.1f}</td><td>{dd['steel']['Ad2']:.1f}</td></tr>
            <tr><td>Conc(Tr)</td><td>{dd['conc']['A']:.2f}</td><td>{dd['conc']['y']:.2f}</td><td>{dd['conc']['Ay']:.1f}</td><td>{dd['conc']['Io']:.1f}</td><td>{dd['conc']['Ad2']:.1f}</td></tr>
            <tr style='background-color:#eee'><td><b>SUMA</b></td><td><b>{dd['sum']['A']:.2f}</b></td><td>-</td><td><b>{dd['sum']['Ay']:.1f}</b></td><td>-</td><td>-</td></tr>
            </table>
            """

        html = f"""{css}
        <h3>MEMORIA DE CÁLCULO</h3>
        
        <h4>1. ANCHO EFECTIVO (AISC I3.1a)</h4>
        <div class="step">L/4: {b_steps['L_4']}</div>
        <div class="step">Spacing: {b_steps['spacing']}</div>
        <div class="result">{b_steps['final']}</div>
        
        <h4>2. CARGAS</h4>
        <div class="step">{l_steps['w_u']}</div>
        <div class="result">{l_steps['M_u']}</div>
        
        <h4>3. CONECTORES (AISC I8)</h4>
        <div class="step">Qn: {c_steps['Qn_desc']} = <b>{conn['Qn_unit']:.2f} k</b></div>
        <div class="step">Cant: {c_steps['N_calc']}</div>
        <div class="result">Vh Req: {c_steps['Vh_calc']} -> {conn['percent']:.1f}% Compuesta</div>
        
        <h4>4. FLEXIÓN (AISC I3.2)</h4>
        <div class="step">{f_steps['C_calc']}</div>
        <div class="step">{f_steps['a_calc']}</div>
        <div class="step">{f_steps['Y_calc']}</div>
        <div class="result">PhiMn = {st['phi_Mn']:.1f} k-ft (Ratio: {st['ratio']:.2f})</div>
        
        <h4>5. CORTANTE (AISC G2)</h4>
        <div class="step">{s_steps['Aw_calc']}</div>
        <div class="step">{s_steps['Formula']}</div>
        <div class="step">{s_steps['Vn_calc']}</div>
        <div class="result">{s_steps['PhiVn_calc']} (Ratio: {shear['ratio']:.2f})</div>
        
        <h4>6. DEFLEXIONES (AISC I3.2 / C-I3-1)</h4>
        
        <div class="step"><b>Propiedades:</b></div>
        <div class="step">Ec = 57000 * sqrt({fc_psi:.0f}) / 1000 = <b>{Ec:.1f} ksi</b></div>
        <div class="step">n = Es / Ec = 29000 / {Ec:.1f} = <b>{n_base:.2f}</b></div>
        <br>
        
        <div class="result">A. Corto Plazo (n={defs['short']['data']['n']:.2f})</div>
        <div class="step">Ancho Equiv. ($b_{{tr}}$) = {b_eff:.1f} / {defs['short']['data']['n']:.2f} = <b>{defs['short']['data']['b_tr']:.2f} in</b></div>
        {mk_tbl(defs['short']['data'])}
        <div class="step">Itr={defs['short']['data']['I_tr']:.1f}, <b>Ieff={defs['short']['data']['I_eff']:.1f} in⁴</b></div>
        <div class="result">Def = {defs['short']['delta']:.3f}" (Lim {defs['short']['limit']:.3f}")</div>
        
        <div class="result" style="margin-top:10px;">B. Largo Plazo (n={defs['long']['data']['n']:.2f})</div>
        <div class="step">Ancho Equiv. ($b_{{tr}}$) = {b_eff:.1f} / {defs['long']['data']['n']:.2f} = <b>{defs['long']['data']['b_tr']:.2f} in</b></div>
        {mk_tbl(defs['long']['data'])}
        <div class="step">Itr={defs['long']['data']['I_tr']:.1f}, <b>Ieff={defs['long']['data']['I_eff']:.1f} in⁴</b></div>
        <div class="result">Def = {defs['long']['delta']:.3f}" (Lim {defs['long']['limit']:.3f}")</div>
        
        <h4>7. RESUMEN</h4>
        <div>Flexión: {st['ratio']:.2f} [{st['status']}]</div>
        <div>Cortante: {shear['ratio']:.2f} [{'OK' if shear['ratio']<=1 else 'FAIL'}]</div>
        <div>Deflexión: {max(defs['short']['ratio'], defs['long']['ratio']):.2f} [{'OK' if defs['short']['ratio']<=1 else 'CHECK'}]</div>
        """
        self.view.report_label.setText(html)

    def export_to_pdf(self):
        if not self.last_results: return
        filename, _ = QFileDialog.getSaveFileName(self.view, "Guardar Reporte", "", "PDF Files (*.pdf)")
        if filename:
            try:
                temp_moment = "temp_diagrams.png"
                temp_section = "temp_section.png"
                self.view.diagram_widget.figure.savefig(temp_moment, dpi=300, bbox_inches='tight')
                self.view.section_widget.figure.savefig(temp_section, dpi=300, bbox_inches='tight')
                
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