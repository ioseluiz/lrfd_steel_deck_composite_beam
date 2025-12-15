import numpy as np

class CompositeBeamDesign:
    """
    Modelo de cálculo LRFD para vigas compuestas (AISC 360-16).
    Soporta conectores tipo Stud y Channel.
    Maneja orientación de Ribs (Perpendicular/Paralelo).
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
        
        self.connector_type = inputs.get('connector_type', 'Stud')
        self.connector_spacing = inputs.get('connector_spacing', 12.0)
        self.connector_props = inputs.get('connector_props', {})
        
        self.deck_orient = inputs.get('deck_orientation', 'Perpendicular')

    def calculate_loads(self):
        w_u = self.s * (1.2 * self.DL + 1.6 * self.LL) / 1000 # kips/ft
        M_u = (w_u * self.L**2) / 8
        V_u = (w_u * self.L) / 2
        
        return {
            "w_u": w_u, "M_u": M_u, "V_u": V_u,
            "steps": {
                "w_u": f"Wu = S * (1.2*DL + 1.6*LL) = {self.s} * (1.2*{self.DL} + 1.6*{self.LL}) / 1000 = {w_u:.2f} kips/ft",
                "M_u": f"Mu = (Wu * L^2) / 8 = ({w_u:.2f} * {self.L}^2) / 8 = {M_u:.2f} k-ft"
            }
        }

    def get_effective_width(self):
        val1 = (self.L * 12) / 4
        val2 = self.s * 12
        b_eff = min(val1, val2)
        return b_eff, f"min(L/4, S) = min({val1:.1f}, {val2:.1f})"

    def calculate_connectors(self):
        wc = 145 
        Ec = 33 * (wc**1.5) * np.sqrt(self.fc * 1000) / 1000 
        
        Qn = 0.0
        formula_str = ""
        subst_str = ""
        
        if self.connector_type == 'Stud':
            d_stud = self.connector_props.get('diameter', 0.75)
            Fu_stud = self.connector_props.get('fu', 65.0)
            Asc = np.pi * (d_stud**2) / 4.0
            
            # --- CORRECCIÓN H_s ---
            # El código anterior usaba hr + 1.5. El ejemplo PDF usa hr + 2.0 (5.0" para 3" deck).
            # Ajustamos a hr + 2.0 para alinearnos con prácticas comunes y el ejemplo.
            Hs = self.hr + 2.0 
            
            if self.deck_orient == 'Perpendicular':
                # Reduction = (0.85 / sqrt(Nr)) * (wr/hr) * (Hs/hr - 1) <= 1.0
                Nr = 1 # Asumido
                rd_factor = (0.85 / np.sqrt(Nr)) * (self.wr / self.hr) * ((Hs / self.hr) - 1)
                rd_factor = min(rd_factor, 1.0)
                formula_str = f"Stud Perp (Hs={Hs}\"): Reducción * 0.5*Asc*sqrt(fc*Ec)"
                
            else: # Parallel
                rd_factor = 0.6 * (self.wr / self.hr) * ((Hs / self.hr) - 1)
                rd_factor = min(rd_factor, 1.0)
                formula_str = f"Stud Parallel (Hs={Hs}\"): Reducción * 0.5*Asc*sqrt(fc*Ec)"
            
            Qn_base = 0.5 * Asc * np.sqrt(self.fc * Ec)
            Qn_limit = Asc * Fu_stud
            
            Qn = min(Qn_base * rd_factor, Qn_limit)
            subst_str = f"Reducción: {rd_factor:.2f} (Hs={Hs}\"). Base: {Qn_base:.1f} k"
            
        elif self.connector_type == 'Channel':
            tf = self.connector_props.get('tf', 0.0)
            tw = self.connector_props.get('tw', 0.0)
            La = self.connector_props.get('length', 0.0)
            Qn = 0.3 * (tf + 0.5*tw) * La * np.sqrt(self.fc * Ec)
            formula_str = "0.3 * (tf + 0.5tw) * La * sqrt(fc*Ec)"
            subst_str = f"0.3*({tf}+0.5*{tw})*{La}*sqrt..."

        N_half = int((self.L * 12 / 2) / self.connector_spacing)
        Total_Qn = N_half * Qn
        
        b_eff, _ = self.get_effective_width()
        
        if self.deck_orient == 'Parallel':
            Ac_ribs = b_eff * (self.wr / 12.0) * self.hr
            Ac = (b_eff * self.tc) + Ac_ribs
        else:
            Ac = b_eff * self.tc
            
        As = self.beam_props['A']
        
        Vh_conc = 0.85 * self.fc * Ac
        Vh_steel = As * self.fy
        Vh_req = min(Vh_conc, Vh_steel)
        
        ratio = Vh_req / Total_Qn if Total_Qn > 0 else 999.0
        
        return {
            "Qn_unit": Qn,
            "N_half": N_half,
            "Total_Qn": Total_Qn,
            "Vh_req": Vh_req,
            "ratio": ratio,
            "type": self.connector_type,
            "is_full_composite": Total_Qn >= Vh_req,
            "Ac_used": Ac,
            "steps": {
                "Qn_f": formula_str,
                "Qn_s": subst_str,
                "Vh_conc": f"0.85 * {self.fc} * {Ac:.1f} = {Vh_conc:.1f} k",
                "Vh_steel": f"{As} * {self.fy} = {Vh_steel:.1f} k",
                "Vh_ctrl": f"min({Vh_conc:.1f}, {Vh_steel:.1f}) = {Vh_req:.1f} k",
                "Sum_Qn": f"{N_half} studs * {Qn:.1f} k = {Total_Qn:.1f} k"
            }
        }

    def _calculate_block_geometry(self, C, b_eff):
        """Calcula profundidad 'a' y distancia centroide 'dist_top' para una fuerza C dada."""
        dist_centroid_from_top = 0.0
        a = 0.0
        
        if self.deck_orient == 'Perpendicular':
            # Solo Losa
            a = C / (0.85 * self.fc * b_eff)
            dist_centroid_from_top = a / 2
            desc = f"a = {C:.1f} / (0.85*{self.fc}*{b_eff:.1f}) = {a:.2f} in"
            
        else: # Parallel
            C_slab_capacity = 0.85 * self.fc * b_eff * self.tc
            
            if C <= C_slab_capacity:
                a = C / (0.85 * self.fc * b_eff)
                dist_centroid_from_top = a / 2
                desc = f"a = {a:.2f} in (En Losa)"
            else:
                C_rem = C - C_slab_capacity
                b_ribs = b_eff * (self.wr / 12.0)
                a_rib = C_rem / (0.85 * self.fc * b_ribs)
                a = self.tc + a_rib
                
                A1 = b_eff * self.tc
                y1 = self.tc / 2.0
                A2 = b_ribs * a_rib
                y2 = self.tc + (a_rib / 2.0)
                dist_centroid_from_top = (A1*y1 + A2*y2) / (A1 + A2)
                desc = f"a = {a:.2f} in (Losa+Ribs, Forma T)"
        
        return a, dist_centroid_from_top, desc

    def check_composite_strength(self, M_u):
        conn_data = self.calculate_connectors()
        steps = {}
        b_eff, b_eff_step = self.get_effective_width()
        steps['b_eff'] = b_eff_step
        d = self.beam_props['d']
        total_conc_h = self.hr + self.tc

        # --- CÁLCULO 1: DISEÑO REAL (Basado en studs provistos) ---
        C_real = min(conn_data['Total_Qn'], conn_data['Vh_req'])
        a_real, dist_real, desc_real = self._calculate_block_geometry(C_real, b_eff)
        
        Y2_real = total_conc_h - dist_real
        Mn_real = C_real * (d/2 + Y2_real) / 12.0
        PhiMn_real = 0.9 * Mn_real
        
        steps['C_force'] = f"C (Real) = {C_real:.1f} kips"
        steps['a'] = desc_real
        steps['Y2'] = f"Y2 = {total_conc_h} - {dist_real:.2f} = {Y2_real:.2f} in"
        steps['arm'] = f"Brazo = {d/2:.2f} + {Y2_real:.2f} = {d/2 + Y2_real:.2f} in"
        steps['Mn'] = f"Mn = {Mn_real:.1f} k-ft"
        steps['PhiMn'] = f"PhiMn = {PhiMn_real:.1f} k-ft"

        # --- CÁLCULO 2: FULL COMPOSITE (Teórico Max) ---
        # Esto sirve para comparar con el ejemplo del PDF cuando Tmax gobierna
        C_full = conn_data['Vh_req'] # min(AsFy, 0.85fcAc)
        a_full, dist_full, desc_full = self._calculate_block_geometry(C_full, b_eff)
        Y2_full = total_conc_h - dist_full
        Mn_full = C_full * (d/2 + Y2_full) / 12.0
        PhiMn_full = 0.9 * Mn_full

        ratio_flex = M_u / PhiMn_real if PhiMn_real > 0 else 999.0
        
        return {
            "phi_Mn": PhiMn_real,
            "ratio": ratio_flex,
            "b_eff": b_eff,
            "a": a_real, 
            "status": "OK" if ratio_flex <= 1.0 else "FALLA",
            "percent_composite": (C_real / conn_data['Vh_req']) * 100 if conn_data['Vh_req'] > 0 else 0,
            "calc_steps": steps,
            "C_force": C_real,
            
            # Datos Full Composite para referencia
            "C_full": C_full,
            "a_full": a_full,
            "phi_Mn_full": PhiMn_full
        }

    def calculate_shear_stud_capacity(self):
        data = self.calculate_connectors()
        return data['Qn_unit']