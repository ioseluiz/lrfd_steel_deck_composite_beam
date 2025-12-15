from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import matplotlib.patches as patches

class DiagramWidget(FigureCanvas):
    def __init__(self, parent=None, width=6, height=8, dpi=100):
        # Aumentamos la altura (height=8) para acomodar 3 gráficos verticalmente
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        # Crear 3 subplots compartiendo el eje X
        self.ax_shear = self.fig.add_subplot(311)
        self.ax_moment = self.fig.add_subplot(312, sharex=self.ax_shear)
        self.ax_deflection = self.fig.add_subplot(313, sharex=self.ax_shear)
        
        # Ajustar espacios
        self.fig.subplots_adjust(hspace=0.4, top=0.95, bottom=0.1)
        
        super().__init__(self.fig)

    def plot_diagrams(self, L, wu, w_service, Ix, E_ksi=29000):
        """
        L: Longitud (ft)
        wu: Carga última factorizada (kips/ft)
        w_service: Carga de servicio (kips/ft)
        Ix: Inercia (in^4)
        E_ksi: Módulo de Elasticidad (ksi)
        """
        # Limpiar ejes
        self.ax_shear.clear()
        self.ax_moment.clear()
        self.ax_deflection.clear()
        
        # Datos eje X
        x = np.linspace(0, L, 200) # pies
        
        # --- 1. CORTANTE (Shear) ---
        R = wu * L / 2
        V = R - wu * x
        
        self.ax_shear.plot(x, V, color='#d62728', lw=2)
        self.ax_shear.fill_between(x, V, 0, color='#d62728', alpha=0.1)
        self.ax_shear.set_ylabel('Cortante (kips)', fontsize=9, fontweight='bold')
        self.ax_shear.set_title('Diagrama de Cortante (Vu)', fontsize=10)
        self.ax_shear.grid(True, linestyle='--', alpha=0.6)
        self.ax_shear.axhline(0, color='black', linewidth=0.8)

        # --- 2. MOMENTO (Moment) ---
        M = (wu * x / 2) * (L - x)
        max_m = np.max(M)
        
        self.ax_moment.plot(x, M, color='#1f77b4', lw=2)
        self.ax_moment.fill_between(x, M, 0, color='#1f77b4', alpha=0.1)
        self.ax_moment.set_ylabel('Momento (k-ft)', fontsize=9, fontweight='bold')
        self.ax_moment.set_title(f'Diagrama de Momento (Mu) - Max: {max_m:.1f} k-ft', fontsize=10)
        self.ax_moment.grid(True, linestyle='--', alpha=0.6)

        # --- 3. DEFLEXIÓN (Deflection) ---
        w_in = w_service / 12.0
        L_in = L * 12.0
        x_in = x * 12.0
        
        delta = -1 * (w_in * x_in / (24 * E_ksi * Ix)) * (L_in**3 - 2*L_in*(x_in**2) + x_in**3)
        max_def = np.min(delta)
        
        self.ax_deflection.plot(x, delta, color='#2ca02c', lw=2)
        self.ax_deflection.fill_between(x, delta, 0, color='#2ca02c', alpha=0.1)
        self.ax_deflection.set_ylabel('Deflexión (in)', fontsize=9, fontweight='bold')
        self.ax_deflection.set_xlabel('Distancia (ft)', fontsize=10)
        self.ax_deflection.set_title(f'Deflexión de Servicio - Max: {max_def:.3f} in', fontsize=10)
        self.ax_deflection.grid(True, linestyle='--', alpha=0.6)
        self.ax_deflection.set_ylim(min(delta)*1.2, 0) 

        self.draw()

class CrossSectionWidget(FigureCanvas):
    # Mantenemos este widget simple para la pestaña "Sección" rápida
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        
    def draw_section(self, inputs, pna_bottom=None):
        self.axes.clear()
        d = inputs['beam_properties']['d']
        bf = inputs['beam_properties']['bf']
        tf = inputs['beam_properties']['tf']
        tw = inputs['beam_properties']['tw']
        tc = inputs['slab_thickness']
        hr = inputs['rib_height']
        wr = inputs['rib_width']
        
        color_steel = '#4F4F4F'
        self.axes.add_patch(patches.Rectangle((-tw/2, 0), tw, d, color=color_steel))
        self.axes.add_patch(patches.Rectangle((-bf/2, 0), bf, tf, color=color_steel))
        self.axes.add_patch(patches.Rectangle((-bf/2, d-tf), bf, tf, color=color_steel))
        
        color_conc = '#E0E0E0' 
        color_deck = '#333333'
        
        self.axes.add_patch(patches.Rectangle((-12, d+hr), 24, tc, color=color_conc, ec=color_deck))
        self.axes.add_patch(patches.Rectangle((-wr/2, d), wr, hr, color=color_conc, ec=color_deck))
        
        if pna_bottom is not None:
            self.axes.axhline(pna_bottom, color='red', linestyle='--', linewidth=1.5)
            self.axes.text(-16, pna_bottom, "PNA", color='red', va='center', ha='right', fontweight='bold')

        self.axes.set_xlim(-20, 20)
        self.axes.set_ylim(-5, d + hr + tc + 5)
        self.axes.set_aspect('equal')
        self.axes.axis('off')
        self.axes.set_title("Sección Transversal Simplificada", fontsize=10)
        self.draw()

class SteelTipsFiguresWidget(FigureCanvas):
    """
    Widget que renderiza las 4 figuras del documento 'Steel Tips':
    1. Planta (Beam Spacing)
    2. Sección Efectiva (Effective Width)
    3. Detalle Deck (Ribs & Studs/Channels)
    4. Diagrama de Fuerzas (Plastic Stress)
    """
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        # Grid 2x2
        self.ax1 = self.fig.add_subplot(221) # Planta
        self.ax2 = self.fig.add_subplot(222) # Sección Efectiva
        self.ax3 = self.fig.add_subplot(223) # Detalle Deck
        self.ax4 = self.fig.add_subplot(224) # Diagrama Fuerzas
        
        self.fig.subplots_adjust(hspace=0.3, wspace=0.3, left=0.05, right=0.95, top=0.92, bottom=0.05)
        super().__init__(self.fig)

    def plot_figures(self, inputs, results):
        # Desempaquetar datos
        L = inputs['span_ft']
        S = inputs['spacing_ft']
        
        beam = inputs['beam_properties']
        d = beam['d']
        bf = beam['bf']
        tf = beam['tf']
        tw = beam['tw']
        
        tc = inputs['slab_thickness']
        hr = inputs['rib_height']
        wr = inputs['rib_width']
        
        b_eff = results['strength']['b_eff']
        a = results['strength']['a']
        
        # Info Conectores
        c_type = inputs.get('connector_type', 'Stud')
        c_props = inputs.get('connector_props', {})
        
        # Limpiar ejes
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()
            ax.axis('off') # Apagar ejes por defecto para dibujar estilo CAD
            ax.set_aspect('equal')

        # --- FIGURA 1: Planta (Plan View) ---
        self._plot_fig1_plan(self.ax1, L, S)

        # --- FIGURA 2: Sección Efectiva (Effective Width) ---
        self._plot_fig2_eff_width(self.ax2, d, bf, tf, tw, tc, hr, b_eff)

        # --- FIGURA 3: Detalle Deck (Ribs & Studs/Channels) ---
        Hs = hr + 2.0 # Altura asumida para stud (como referencia de espacio)
        self._plot_fig3_deck_detail(self.ax3, tc, hr, wr, Hs, c_type, c_props)

        # --- FIGURA 4: Diagrama de Fuerzas (Plastic Stress) ---
        # Calcular Y2 desde resultados
        total_h = d + hr + tc
        # PNA location from bottom
        # Usamos 'a' (profundidad bloque) para ubicar C
        
        self._plot_fig4_forces(self.ax4, d, hr, tc, a, results)

        self.draw()

    def _plot_fig1_plan(self, ax, L, S):
        ax.set_title("Figura 1: Planta Típica", fontsize=10, fontweight='bold')
        
        # Dibujar vigas como líneas
        num_beams = 3
        margin = S * 0.5
        total_width = S * (num_beams - 1) + 2*margin
        
        # Girders verticales a izq y der
        ax.plot([0, 0], [0, total_width], color='black', lw=2) # Girder Left
        ax.plot([L, L], [0, total_width], color='black', lw=2) # Girder Right
        
        # Vigas interiores horizontales
        for i in range(num_beams):
            y = margin + i * S
            ax.plot([0, L], [y, y], color='blue', lw=1.5)
            ax.text(L/2, y + S*0.1, "Viga A", color='blue', ha='center', fontsize=8)

        # --- COTAS MEJORADAS ---
        # Span (Flecha L)
        dim_y = -S * 0.3 # Posición Y de la flecha (debajo de las vigas)
        
        # Dibujar flecha de doble punta explícita de 0 a L
        ax.annotate('', xy=(0, dim_y), xytext=(L, dim_y),
                    arrowprops=dict(arrowstyle='<|-|>', color='black', lw=1.2))
        
        # Texto debajo de la flecha
        ax.text(L/2, dim_y - S*0.15, f'Span L = {L} ft', ha='center', va='top', fontsize=9, color='black')
        
        # Spacing
        y_mid = margin + S
        ax.annotate(f's = {S} ft', xy=(-L*0.1, y_mid), xytext=(-L*0.1, y_mid - S),
                    arrowprops=dict(arrowstyle='<->'), va='center', rotation=90)

        ax.set_xlim(-L*0.2, L*1.2)
        ax.set_ylim(-S, total_width + S*0.5)

    def _plot_fig2_eff_width(self, ax, d, bf, tf, tw, tc, hr, b_eff):
        ax.set_title("Figura 2: Ancho Efectivo", fontsize=10, fontweight='bold')
        
        # Dibujar Viga I
        color_steel = '#555'
        ax.add_patch(patches.Rectangle((-tw/2, 0), tw, d, color=color_steel)) # Web
        ax.add_patch(patches.Rectangle((-bf/2, 0), bf, tf, color=color_steel)) # Bot Flange
        ax.add_patch(patches.Rectangle((-bf/2, d-tf), bf, tf, color=color_steel)) # Top Flange
        
        # Losa Efectiva
        # Dibujar losa ancha b_eff
        
        # Losa
        ax.add_patch(patches.Rectangle((-b_eff/2, d+hr), b_eff, tc, color='#ddd', ec='black'))
        
        # Haunch (Rib)
        ax.add_patch(patches.Rectangle((-2, d), 4, hr, color='#ddd', ec='black')) # Rib simplificado
        
        # Cotas
        y_dim = d + hr + tc + 2
        ax.annotate(f'b = {b_eff:.1f}"', xy=(-b_eff/2, y_dim), xytext=(b_eff/2, y_dim),
                    arrowprops=dict(arrowstyle='<->'), ha='center')
        
        ax.text(b_eff/2 + 2, d + hr + tc/2, f"tc={tc}\"", va='center', fontsize=8)
        ax.text(4, d + hr/2, f"hr={hr}\"", va='center', fontsize=8)

        ax.set_xlim(-b_eff/1.5, b_eff/1.5)
        ax.set_ylim(-2, d + hr + tc + 10)

    def _plot_fig3_deck_detail(self, ax, tc, hr, wr, Hs, c_type, c_props):
        """Dibuja el detalle del rib con el conector apropiado (Stud o Channel)"""
        ax.set_title(f"Figura 3: Detalle Conector ({c_type})", fontsize=10, fontweight='bold')
        
        # Dibujar perfil del deck ondulado (Trapezoidal)
        rib_pitch = 12.0 # Standard
        start_x = -rib_pitch
        
        y_bot = 0
        y_top = hr
        
        # Losa sólida
        ax.add_patch(patches.Rectangle((start_x, y_top), rib_pitch*2.5, tc, color='#eee', ec='none'))
        
        # Dibujar linea deck
        deck_line_x = []
        deck_line_y = []
        
        for i in range(3):
            x_base = start_x + i*rib_pitch
            
            # Puntos del rib
            x1 = x_base
            x2 = x_base + (rib_pitch-wr)/2
            x3 = x2
            x4 = x_base + (rib_pitch+wr)/2
            x5 = x4
            x6 = x_base + rib_pitch
            
            deck_line_x.extend([x1, x2, x3, x4, x5, x6])
            deck_line_y.extend([y_top, y_top, y_bot, y_bot, y_top, y_top])
            
            # Relleno de concreto en el rib
            rib_poly = patches.Polygon([
                [x2, y_top],
                [x2 + 0.5, y_bot], # Ligeramente trapezoidal
                [x4 - 0.5, y_bot],
                [x4, y_top]
            ], closed=True, color='#eee', ec='none')
            ax.add_patch(rib_poly)
            
            # --- DIBUJAR CONECTOR EN EL RIB CENTRAL ---
            if i == 1:
                center_x = (x2 + x4) / 2
                
                if c_type == 'Stud':
                    # Dibujo de Stud (Poste con cabeza)
                    stud_h = Hs # Altura nominal
                    # Cuerpo
                    ax.plot([center_x, center_x], [y_bot, y_bot + stud_h], color='black', lw=2)
                    # Cabeza
                    ax.plot([center_x-0.4, center_x+0.4], [y_bot + stud_h, y_bot + stud_h], color='black', lw=4)
                    # Cota
                    ax.text(center_x + 1, y_bot + stud_h/2, f"Hs={stud_h}\"", fontsize=8)
                    
                elif c_type == 'Channel':
                    # Dibujo de Channel (C-Shape)
                    chan_h = min(3.0, hr - 0.5) 
                    chan_len = c_props.get('length', 4.0) # Longitud La
                    
                    rect_w = chan_len if chan_len < wr else wr - 1 # Ajuste visual
                    rect_x = center_x - rect_w/2
                    
                    # Cuerpo del canal (Rectángulo relleno)
                    ax.add_patch(patches.Rectangle((rect_x, y_bot), rect_w, chan_h, color='#555', ec='black'))
                    
                    # Etiqueta
                    ax.text(center_x, y_bot + chan_h + 0.5, f"Channel\nL={chan_len}\"", ha='center', fontsize=8)

        ax.plot(deck_line_x, deck_line_y, color='black', lw=1)
        
        # Cota wr
        center_rib_x = start_x + rib_pitch + rib_pitch/2
        ax.annotate(f'wr={wr}"', xy=(center_rib_x - wr/2, y_bot-0.5), xytext=(center_rib_x + wr/2, y_bot-0.5),
                    arrowprops=dict(arrowstyle='<->'), ha='center')

        ax.set_xlim(-5, 20)
        ax.set_ylim(-2, hr + tc + 2)

    def _plot_fig4_forces(self, ax, d, hr, tc, a, results):
        ax.set_title("Figura 4: Distribución de Fuerzas", fontsize=10, fontweight='bold')
        
        total_h = d + hr + tc
        
        # 1. Diagrama de la sección (Esquemático vertical)
        x_sec = 0
        ax.plot([x_sec, x_sec], [0, total_h], color='black', lw=1)
        # Flanges
        ax.plot([x_sec-1, x_sec+1], [0, 0], color='black') # Bot
        ax.plot([x_sec-1, x_sec+1], [d, d], color='black') # Top Steel
        ax.plot([x_sec-2, x_sec+2], [total_h, total_h], color='black') # Top Conc
        
        # 2. Bloque de Compresión (C)
        x_force = 4
        y_top = total_h
        y_bot_a = total_h - a
        
        # Bloque C (Sombreado)
        ax.add_patch(patches.Rectangle((x_force, y_bot_a), 2, a, color='#ffcccc', ec='red'))
        
        # Flecha C
        c_y = y_top - a/2
        ax.arrow(x_force + 4, c_y, -2, 0, head_width=1, head_length=0.5, fc='red', ec='red')
        
        # Valor de C (Manejo seguro de la clave C_force)
        c_val = results.get('C_force', 0.0) 
        if c_val == 0.0 and 'strength' in results and 'C_force' in results['strength']:
             # Fallback por si la estructura de datos varía
             c_val = results['strength']['C_force']
             
        ax.text(x_force + 4.5, c_y, f"C = {c_val:.1f} k", color='red', va='center', fontsize=8)
        
        # 3. Flecha T (Tensión)
        t_y = d/2
        ax.arrow(x_force + 4, t_y, -2, 0, head_width=1, head_length=0.5, fc='blue', ec='blue')
        ax.text(x_force + 4.5, t_y, "T = AsFy", color='blue', va='center', fontsize=8)
        
        # 4. Cotas
        ax.annotate(f'a={a:.2f}"', xy=(x_force-0.5, y_top), xytext=(x_force-0.5, y_bot_a),
                    arrowprops=dict(arrowstyle='<->'), ha='center', color='red')
        
        ax.annotate(f'Brazo', xy=(x_force + 1, t_y), xytext=(x_force + 1, c_y),
                    arrowprops=dict(arrowstyle='<->'), ha='center')

        ax.set_xlim(-5, 15)
        ax.set_ylim(-2, total_h + 2)