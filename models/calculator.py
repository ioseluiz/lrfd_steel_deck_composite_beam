import numpy as np

class CompositeBeamDesign:
    """
    Modelo de cálculo LRFD para vigas compuestas (AISC 360-16).
    Incluye cálculo detallado de Sección Transformada para deflexiones.
    """
    def __init__(self, inputs):
        self.inputs = inputs
        # Geometría y Materiales
        self.L = inputs['span_ft']
        self.s = inputs['spacing_ft']
        self.tc = inputs['slab_thickness']
        self.fc = inputs['fc_ksi']
        self.fy = inputs['fy_ksi']
        self.wr = inputs['rib_width']
        self.hr = inputs['rib_height']
        self.DL = inputs['dl_psf']
        self.LL = inputs['ll_psf']
        self.beam_props = inputs['beam_properties']
        
        # Propiedades del Acero
        self.Es = 29000.0 # ksi
        self.As = self.beam_props['A']
        self.d = self.beam_props['d']
        self.Ix = self.beam_props['Ix']
        self.tw = self.beam_props['tw'] # Necesario para cortante
        
        # Conectores
        self.connector_type = inputs.get('connector_type', 'Stud')
        self.connector_spacing = inputs.get('connector_spacing', 12.0)
        self.connector_props = inputs.get('connector_props', {})
        self.deck_orient = inputs.get('deck_orientation', 'Perpendicular')

    def calculate_loads(self):
        w_u = self.s * (1.2 * self.DL + 1.6 * self.LL) / 1000 # kips/ft
        w_service = self.s * (self.DL + self.LL) / 1000 # kips/ft
        
        M_u = (w_u * self.L**2) / 8
        V_u = (w_u * self.L) / 2
        
        return {
            "w_u": w_u, "M_u": M_u, "V_u": V_u, "w_service": w_service,
            "steps": {
                "w_u": f"Wu = {self.s}' * (1.2*{self.DL} + 1.6*{self.LL}) / 1000 = {w_u:.2f} klf (ASCE 7)",
                "M_u": f"Mu = ({w_u:.2f} * {self.L}^2) / 8 = {M_u:.2f} k-ft"
            }
        }

    def get_effective_width(self):
        # AISC I3.1a
        L_span = self.L * 12
        spacing_center = self.s * 12
        val1 = L_span / 4
        val2 = spacing_center
        b_eff = min(val1, val2)
        
        steps = {
            "L_4": f"L/4 = {L_span:.1f} / 4 = {val1:.1f} in",
            "spacing": f"Espaciamiento = {val2:.1f} in",
            "final": f"b_eff = min({val1:.1f}, {val2:.1f}) = {b_eff:.1f} in [AISC I3.1a]"
        }
        return b_eff, steps

    def calculate_connectors(self):
        # --- Cálculo Ec (ACI 318) ---
        fc_psi = self.fc * 1000
        Ec = 57000.0 * np.sqrt(fc_psi) / 1000.0 
        
        Qn = 0.0
        formula_desc = ""
        Hs = self.hr + 2.0 
        
        unit_name = "studs"
        ref_aisc = "I8.2a"
        
        if self.connector_type == 'Stud':
            unit_name = "studs"
            ref_aisc = "I8.2a"
            d_stud = self.connector_props.get('diameter', 0.75)
            Fu_stud = self.connector_props.get('fu', 65.0)
            Asc = np.pi * (d_stud**2) / 4.0
            
            reduction = 1.0
            if self.deck_orient == 'Perpendicular':
                term = (0.85 / np.sqrt(1)) * (self.wr/self.hr) * ((Hs/self.hr)-1)
                reduction = min(1.0, term)
            else: # Parallel
                term = 0.6 * (self.wr/self.hr) * ((Hs/self.hr)-1)
                reduction = min(1.0, term)
            
            Qn_conc = 0.5 * Asc * np.sqrt(self.fc * Ec)
            Qn_steel = Asc * Fu_stud 
            
            Qn = min(Qn_conc, Qn_steel) * reduction
            formula_desc = f"Stud {d_stud}\": min(0.5Asc√(f'cEc), AscFu)*RgRp"

        elif self.connector_type == 'Channel':
            unit_name = "channels"
            ref_aisc = "I8.2b"
            tf = self.connector_props.get('tf', 0.0)
            tw = self.connector_props.get('tw', 0.0)
            La = self.connector_props.get('length', 0.0)
            Qn = 0.3 * (tf + 0.5*tw) * La * np.sqrt(self.fc * Ec)
            formula_desc = "Channel: 0.3(tf+0.5tw)La√(f'cEc)"

        N_half = int((self.L * 12 / 2) / self.connector_spacing)
        Sum_Qn = N_half * Qn
        
        b_eff, _ = self.get_effective_width()
        Ac = b_eff * self.tc 
        
        Vh_conc = 0.85 * self.fc * Ac
        Vh_steel = self.As * self.fy
        Vh_req = min(Vh_conc, Vh_steel)
        
        percent_composite = min(100.0, (Sum_Qn / Vh_req) * 100.0) if Vh_req > 0 else 0
        
        return {
            "Qn_unit": Qn, "N_half": N_half, "Sum_Qn": Sum_Qn, "Vh_req": Vh_req,
            "percent": percent_composite, "Ec": Ec,
            "steps": {
                "Qn_desc": f"{formula_desc} [AISC {ref_aisc}]",
                "Vh_calc": f"min(0.85f'cAc, AsFy) = min({Vh_conc:.1f}, {Vh_steel:.1f}) [AISC I3.2d]",
                "N_calc": f"({self.L}'/2) / ({self.connector_spacing}\"/12) = {N_half} {unit_name}"
            }
        }

    def check_composite_strength(self, M_u, conn_data):
        b_eff, _ = self.get_effective_width()
        C_force = min(conn_data['Sum_Qn'], conn_data['Vh_req'])
        
        a = C_force / (0.85 * self.fc * b_eff) if b_eff > 0 else 0
        
        dist_C_top = a / 2
        dist_T_top = self.hr + self.tc + (self.d / 2)
        
        Y = dist_T_top - dist_C_top
        Mn = C_force * Y / 12.0 
        PhiMn = 0.9 * Mn
        ratio = M_u / PhiMn if PhiMn > 0 else 999
        
        steps = {
            "C_calc": f"C = min(SumQn, Vh_req) = {C_force:.1f} kips",
            "a_calc": f"a = C / (0.85 f'c b) = {a:.3f} in",
            "Y_calc": f"Brazo = ({self.d/2:.2f} + {self.hr} + {self.tc}) - {a/2:.3f} = {Y:.2f} in",
            "Mn_calc": f"Mn = C * Y = {C_force:.1f} * {Y:.2f} / 12 = {Mn:.1f} k-ft [AISC I3.2]"
        }
        return {"phi_Mn": PhiMn, "ratio": ratio, "a": a, "b_eff": b_eff, 
                "status": "OK" if ratio <= 1.0 else "FALLA", "steps": steps, "C_force": C_force}

    def check_shear_strength(self, V_u):
        """
        Calcula la resistencia a cortante según AISC 360-16 Capítulo G.
        Asume perfiles W laminados (Phi=1.0, Cv1=1.0 para la mayoría de casos en edificación).
        """
        Aw = self.d * self.tw
        # Vn = 0.6 * Fy * Aw * Cv1 (AISC Eq G2-1)
        # Para perfiles W típicos h/tw < 2.24 sqrt(E/Fy), entonces Cv1 = 1.0 y Phi = 1.0
        Cv1 = 1.0
        Phi = 1.0
        
        Vn = 0.6 * self.fy * Aw * Cv1
        PhiVn = Phi * Vn
        
        ratio = V_u / PhiVn if PhiVn > 0 else 999.0
        
        steps = {
            "Aw_calc": f"Area Alma ($A_w$) = d * tw = {self.d} * {self.tw} = {Aw:.2f} in²",
            "Formula": "Vn = 0.6 * Fy * Aw * Cv1 [AISC Eq. G2-1]",
            "Vn_calc": f"Vn = 0.6 * {self.fy} * {Aw:.2f} * {Cv1} = {Vn:.1f} kips",
            "PhiVn_calc": f"$\phi V_n$ = {Phi} * {Vn:.1f} = <b>{PhiVn:.1f} kips</b>"
        }
        
        return {
            "PhiVn": PhiVn,
            "ratio": ratio,
            "status": "OK" if ratio <= 1.0 else "FALLA",
            "steps": steps
        }

    def calculate_transformed_section(self, conn_data, long_term=False):
        Ec = conn_data['Ec']
        n_base = self.Es / Ec
        n = n_base * 2.0 if long_term else n_base 
        
        b_eff, _ = self.get_effective_width()
        b_tr = b_eff / n
        
        A_s = self.As
        y_s = self.d / 2.0
        Ay_s = A_s * y_s
        Io_s = self.Ix 
        
        y_slab = self.d + self.hr + (self.tc / 2.0)
        A_slab_tr = b_tr * self.tc
        I_slab_tr = (b_tr * self.tc**3) / 12.0
        
        A_ribs_tr = 0.0
        y_ribs = 0.0
        I_ribs_tr = 0.0
        
        if self.deck_orient == 'Parallel':
            rib_width_ratio = self.wr / 12.0
            b_tr_ribs = b_tr * rib_width_ratio
            A_ribs_tr = b_tr_ribs * self.hr
            y_ribs = self.d + (self.hr / 2.0)
            I_ribs_tr = (b_tr_ribs * self.hr**3) / 12.0
            
        A_c_tr = A_slab_tr + A_ribs_tr
        if A_c_tr > 0:
            y_c = (A_slab_tr * y_slab + A_ribs_tr * y_ribs) / A_c_tr
            d_slab = y_slab - y_c
            d_ribs = y_ribs - y_c
            I_c_parts = (I_slab_tr + A_slab_tr*d_slab**2) + (I_ribs_tr + A_ribs_tr*d_ribs**2)
            Io_c = I_c_parts
        else:
            y_c = y_slab
            Io_c = I_slab_tr
            
        Sum_A = A_s + A_c_tr
        Sum_Ay = Ay_s + (A_c_tr * y_c)
        Y_bar = Sum_Ay / Sum_A if Sum_A > 0 else 0
        
        d_s = Y_bar - y_s
        Ad2_s = A_s * (d_s**2)
        d_c = y_c - Y_bar
        Ad2_c = A_c_tr * (d_c**2)
        
        I_tr = Io_s + Ad2_s + Io_c + Ad2_c
        
        percent = conn_data['percent']
        I_eff = self.Ix + np.sqrt(percent/100.0) * (I_tr - self.Ix)
        
        return {
            "n": n, "n_base": n_base, "b_tr": b_tr, "Y_bar": Y_bar, "I_tr": I_tr, "I_eff": I_eff,
            "table_data": {
                "steel": {"A": A_s, "y": y_s, "Ay": Ay_s, "Io": Io_s, "Ad2": Ad2_s},
                "conc":  {"A": A_c_tr, "y": y_c, "Ay": A_c_tr*y_c, "Io": Io_c, "Ad2": Ad2_c},
                "sum":   {"A": Sum_A, "Ay": Sum_Ay}
            }
        }

    def calculate_deflections(self, conn_data, loads):
        trans_short = self.calculate_transformed_section(conn_data, long_term=False)
        trans_long = self.calculate_transformed_section(conn_data, long_term=True)
        w_serv = loads['w_service']
        L_in = self.L * 12
        E = self.Es
        
        delta_inst = (5 * (w_serv/12) * L_in**4) / (384 * E * trans_short['I_eff'])
        delta_long = (5 * (w_serv/12) * L_in**4) / (384 * E * trans_long['I_eff'])
        
        limit_360 = L_in / 360.0
        limit_240 = L_in / 240.0
        
        return {
            "short": {"delta": delta_inst, "data": trans_short, "limit": limit_360, "ratio": delta_inst/limit_360, "label_limit": "L/360"},
            "long":  {"delta": delta_long, "data": trans_long, "limit": limit_240, "ratio": delta_long/limit_240, "label_limit": "L/240"}
        }