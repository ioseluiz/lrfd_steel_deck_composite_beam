from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QLineEdit, QComboBox, QPushButton, 
                             QLabel, QTabWidget, QScrollArea, QGroupBox)
from PyQt5.QtCore import Qt
from .plotting_widgets import DiagramWidget, CrossSectionWidget, SteelTipsFiguresWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MetalDeck Pro - Diseño LRFD de Vigas Compuestas")
        self.setGeometry(100, 100, 1300, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout Raíz (Vertical) para permitir pie de página
        root_layout = QVBoxLayout(central_widget)
        
        # Contenedor Principal (Horizontal) para Inputs y Tabs
        content_layout = QHBoxLayout()
        root_layout.addLayout(content_layout)
        
        # --- Panel Izquierdo: Inputs ---
        input_panel = QWidget()
        input_panel.setMaximumWidth(420)
        input_layout = QVBoxLayout(input_panel)
        
        scroll_input = QScrollArea()
        scroll_input.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Grupo 1: Geometría y Cargas
        grp_geo = QGroupBox("Geometría y Cargas")
        form_geo = QFormLayout()
        self.span_input = QLineEdit("30")
        self.spacing_input = QLineEdit("10")
        self.dl_input = QLineEdit("57")
        self.ll_input = QLineEdit("100")
        form_geo.addRow("Luz (ft):", self.span_input)
        form_geo.addRow("Espaciamiento (ft):", self.spacing_input)
        form_geo.addRow("Carga Muerta (psf):", self.dl_input)
        form_geo.addRow("Carga Viva (psf):", self.ll_input)
        grp_geo.setLayout(form_geo)
        scroll_layout.addWidget(grp_geo)

        # Grupo 2: Materiales y Sección
        grp_mat = QGroupBox("Materiales y Sección")
        form_mat = QFormLayout()
        self.fc_input = QLineEdit("3.0")
        self.fy_input = QLineEdit("50")
        self.section_combo = QComboBox()
        self.slab_thick_input = QLineEdit("2.5")
        
        # Deck Inputs
        self.rib_h_input = QLineEdit("3.0")
        self.rib_w_input = QLineEdit("6.0")
        self.deck_orient_combo = QComboBox()
        self.deck_orient_combo.addItems(["Perpendicular", "Parallel"])
        
        form_mat.addRow("f'c (ksi):", self.fc_input)
        form_mat.addRow("Fy (ksi):", self.fy_input)
        form_mat.addRow("Perfil W:", self.section_combo)
        form_mat.addRow("Espesor Losa (in):", self.slab_thick_input)
        form_mat.addRow("Deck Altura (in):", self.rib_h_input)
        form_mat.addRow("Deck Ancho (in):", self.rib_w_input)
        form_mat.addRow("Orientación Ribs:", self.deck_orient_combo)
        
        grp_mat.setLayout(form_mat)
        scroll_layout.addWidget(grp_mat)

        # Grupo 3: Conectores
        grp_conn = QGroupBox("Conectores de Cortante")
        vbox_conn = QVBoxLayout()
        form_conn_main = QFormLayout()
        self.connector_type_combo = QComboBox()
        self.connector_type_combo.addItems(["Stud", "Channel"])
        self.conn_spacing_input = QLineEdit("12") 
        form_conn_main.addRow("Tipo:", self.connector_type_combo)
        form_conn_main.addRow("Espaciamiento (in):", self.conn_spacing_input)
        vbox_conn.addLayout(form_conn_main)
        
        self.stud_params_widget = QWidget()
        form_stud = QFormLayout(self.stud_params_widget)
        self.stud_diam_combo = QComboBox()
        self.stud_diam_combo.addItems(["1/2", "5/8", "3/4", "7/8"])
        self.stud_diam_combo.setCurrentText("3/4")
        self.stud_fu_input = QLineEdit("65")
        form_stud.addRow("Diámetro (in):", self.stud_diam_combo)
        form_stud.addRow("Fu (ksi):", self.stud_fu_input)
        vbox_conn.addWidget(self.stud_params_widget)
        
        self.channel_params_widget = QWidget()
        form_chan = QFormLayout(self.channel_params_widget)
        self.channel_tf_input = QLineEdit("0.3") 
        self.channel_tw_input = QLineEdit("0.2") 
        self.channel_len_input = QLineEdit("4.0") 
        form_chan.addRow("Espesor Ala (in):", self.channel_tf_input)
        form_chan.addRow("Espesor Alma (in):", self.channel_tw_input)
        form_chan.addRow("Longitud (in):", self.channel_len_input)
        vbox_conn.addWidget(self.channel_params_widget)
        self.channel_params_widget.setVisible(False) 
        
        grp_conn.setLayout(vbox_conn)
        scroll_layout.addWidget(grp_conn)
        
        scroll_input.setWidget(scroll_content)
        input_layout.addWidget(scroll_input)

        self.calc_btn = QPushButton("Calcular Diseño")
        self.calc_btn.setStyleSheet("background-color: #007bff; color: white; padding: 12px; font-weight: bold;")
        self.export_btn = QPushButton("Exportar PDF")
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("background-color: #28a745; color: white; padding: 12px; font-weight: bold;")
        
        input_layout.addWidget(self.calc_btn)
        input_layout.addWidget(self.export_btn)
        
        self.tabs = QTabWidget()
        self.report_label = QLabel("Ingrese datos y calcule.")
        self.report_label.setWordWrap(True)
        self.report_label.setStyleSheet("padding: 10px; background: white;")
        self.report_label.setAlignment(Qt.AlignTop)
        
        scroll_rep = QScrollArea()
        scroll_rep.setWidget(self.report_label)
        scroll_rep.setWidgetResizable(True)
        
        self.tabs.addTab(scroll_rep, "Reporte")
        
        # Widget Figuras Steel Tips
        self.steeltips_widget = SteelTipsFiguresWidget()
        self.tabs.addTab(self.steeltips_widget, "Figuras Steel Tips")
        
        self.diagram_widget = DiagramWidget()
        self.tabs.addTab(self.diagram_widget, "Diagramas V/M/D")
        
        self.section_widget = CrossSectionWidget()
        self.tabs.addTab(self.section_widget, "Sección")
        
        # Añadir al content layout (Horizontal)
        content_layout.addWidget(input_panel, 1)
        content_layout.addWidget(self.tabs, 3)
        
        # --- PIE DE PÁGINA (COPYRIGHT) ---
        # Añadir al root layout (Vertical), debajo del contenido
        copyright_label = QLabel("© 2025 Ing. Jose Luis Munoz. Todos los derechos reservados.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            color: #333333; 
            font-size: 11px; 
            margin-top: 5px; 
            margin-bottom: 5px; 
            font-weight: bold;
            background-color: #f0f0f0;
            padding: 5px;
            border-top: 1px solid #ccc;
        """)
        root_layout.addWidget(copyright_label)