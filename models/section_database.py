import csv
import os

class SteelSectionDatabase:
    """
    Maneja la carga de la base de datos de perfiles W del AISC desde un archivo CSV.
    """
    _sections = {}

    @staticmethod
    def get_sections(csv_filename="w_sections.csv"):
        """
        Lee el archivo CSV y retorna un diccionario con las propiedades
        de las secciones W. Carga los datos solo una vez (Singleton pattern).
        """
        # Si ya está cargada en memoria, devolverla directamente
        if SteelSectionDatabase._sections:
            return SteelSectionDatabase._sections

        # --- SOLUCIÓN ROBUSTA PARA RUTAS (WINDOWS/LINUX/MAC) ---
        # 1. Ruta absoluta de ESTE archivo script (models/section_database.py)
        current_file_path = os.path.abspath(__file__)
        
        # 2. Carpeta contenedora 'models' (Padre inmediato)
        models_dir = os.path.dirname(current_file_path)
        
        # 3. Carpeta raíz del proyecto (Padre de 'models')
        project_root = os.path.dirname(models_dir)
        
        # 4. Construir ruta bajando a 'assets' desde la raíz
        csv_path = os.path.join(project_root, "assets", csv_filename)

        # DEBUG: Imprimir la ruta calculada para que puedas verificarla en la consola
        print(f"DEBUG: Buscando base de datos en: {csv_path}")

        # Verificación de seguridad
        if not os.path.exists(csv_path):
            print(f"Error: No se encuentra el archivo en la ruta calculada.")
            # Intento de fallback
            fallback_path = os.path.join(os.getcwd(), "assets", csv_filename)
            print(f"DEBUG: Intentando ruta alternativa (CWD): {fallback_path}")
            
            if os.path.exists(fallback_path):
                 csv_path = fallback_path
            else:
                print("Error Crítico: No se pudo localizar el archivo CSV.")
                return {
                    "W18X35": {"d": 17.7, "tw": 0.3, "bf": 6.0, "tf": 0.425, "A": 10.3, "Ix": 510, "Zx": 66.5}
                }

        # --- MANEJO DE ENCODING INTELIGENTE ---
        # Probamos varios encodings comunes porque Excel en Windows suele usar cp1252
        encodings_to_try = ['utf-8-sig', 'cp1252', 'latin-1']
        
        for encoding in encodings_to_try:
            try:
                current_sections = {}
                print(f"DEBUG: Intentando leer con encoding: {encoding}")
                
                with open(csv_path, mode='r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        # Validar que sea un perfil W
                        type_val = row.get('Type', 'W')
                        # Algunos CSVs pueden tener espacios o mayúsculas diferentes
                        if type_val and type_val.strip().upper() != 'W':
                            continue
                        
                        label = row.get('AISC_Manual_Label')
                        if not label:
                            continue

                        try:
                            # Mapeo de columnas del CSV AISC estándar a las propiedades internas
                            props = {
                                "A": float(row['A']),   # Area
                                "d": float(row['d']),   # Depth
                                "tw": float(row['tw']), # Web thickness
                                "bf": float(row['bf']), # Flange width
                                "tf": float(row['tf']), # Flange thickness
                                "Ix": float(row['Ix']), # Moment of Inertia (x-axis)
                                "Zx": float(row['Zx'])  # Plastic Modulus (x-axis)
                            }
                            current_sections[label] = props
                        except (ValueError, KeyError):
                            # Si alguna celda está vacía o dañada, saltar fila
                            continue
                
                # Si llegamos aquí, la lectura fue exitosa
                SteelSectionDatabase._sections = current_sections
                print(f"Éxito: {len(current_sections)} perfiles cargados usando {encoding}.")
                return current_sections

            except UnicodeDecodeError:
                print(f"Advertencia: Falló encoding {encoding}, intentando siguiente...")
                continue
            except Exception as e:
                print(f"Error leyendo la base de datos CSV con {encoding}: {e}")
                # Intentar el siguiente encoding por si acaso
                continue

        print("Error Crítico: No se pudo leer el archivo con ningún encoding estándar.")
        return {}