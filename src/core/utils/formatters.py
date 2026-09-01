from typing import Optional, Any

class Formatters:
    @staticmethod
    def normalizar_moneda(moneda_str: Optional[Any]) -> Optional[str]:
        """
        Normaliza expresiones monetarias heterogéneas al estándar ISO 4217 (USD o PEN).
        Soporta cadenas con ruido, tildes y variaciones tipográficas comunes de OCR.
        """
        if val_is_none := (moneda_str is None):
            return None
            
        # 1. Blindaje contra tipos no esperados (ej: ints o floats) y remoción de espacios
        m = str(moneda_str).strip().upper()
        if not m:
            return None

        # 2. Remover tildes de forma rápida para simplificar diccionarios de búsqueda
        m = m.replace("Ó", "O").replace("É", "E")

        # 3. Mapeo semántico por subcadenas
        if any(token in m for token in ["US$", "DOLARES", "$", "USD"]):
            return "USD"
            
        if any(token in m for token in ["S/", "SOLES", "PEN"]):
            return "PEN"
            
        # Si no coincide con ninguna divisa conocida, se retorna el texto limpio original
        return m
