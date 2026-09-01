import pymupdf as fitz

def detectar_zonas_ocr_en_pdf_hibrido(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pagina = doc[0]  # Analizamos la primera página
    
    coordenadas_para_ocr = []
    
    # PyMuPDF puede listarnos todos los objetos de tipo 'imagen' incrustados en la página
    # Cada imagen suele ser una firma, un sello o una foto escaneada.
    lista_imagenes = pagina.get_images(full=True)
    
    print(f"Se encontraron {len(lista_imagenes)} imágenes incrustadas en el PDF nativo.")
    
    for img_info in pagina.get_drawings(): # O mediante bounding boxes de gráficos
        pass 

    # Alternativa más precisa: Buscar los "rectángulos" de las imágenes en la página
    for info in pagina.get_image_info():
        # info['bbox'] nos da las coordenadas (x0, y0, x1, y1) de la imagen en la página
        bbox = info['bbox']
        
        # Calculamos la densidad visual interna de ese recuadro para verificar si tiene "tinta"
        # (Así descartamos imágenes transparentes o logotipos blancos de fondo)
        pix_recuadro = pagina.get_pixmap(clip=bbox, colorspace=fitz.csGRAY)
        
        pixeles_tinta = sum(1 for p in pix_recuadro.samples if p < 240)
        total_pixeles = pix_recuadro.width * pix_recuadro.height
        densidad_local = (pixeles_tinta / total_pixeles) * 100 if total_pixeles > 0 else 0
        
        # Si el recuadro tiene suficiente densidad de tinta, es candidato a OCR
        if densidad_local > 5.0:  # Más del 5% de tinta interna
            coordenadas_para_ocr.append({
                "coordenadas": bbox,  # (xmin, ymin, xmax, ymax)
                "densidad": round(densidad_local, 2)
            })
            
    return coordenadas_para_ocr

# Ejemplo de lo que devolvería esta función:
# [
#    {"coordenadas": (45.0, 650.0, 200.0, 750.0), "densidad": 24.5} 
# ]
# -> Esto significa: "Hay una zona densa de imagen al final de la página (y de 650 a 750)"
