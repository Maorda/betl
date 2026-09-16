import asyncio
from playwright.async_api import async_playwright

async def descargar_pdf_desde_visor(url_pagina: str, output_path: str = "documento.pdf"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Visibilidad activa para validar el flujo
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        pdf_bytes = None

        # Interceptor de red para peticiones Blob/PDF
        async def handle_response(response):
            nonlocal pdf_bytes
            content_type = response.headers.get("content-type", "")
            if "application/pdf" in content_type or "blob:" in response.url or response.url.endswith(".pdf"):
                print(f"[+] Capturado PDF/Blob desde la red: {response.url}")
                try:
                    pdf_bytes = await response.body()
                except Exception:
                    pass

        page.on("response", handle_response)

        print(f"[*] Navegando a {url_pagina}...")
        
        # 1. Usar domcontentloaded para evitar bloqueos por conexiones secundarias de SUNARP
        await page.goto(url_pagina, wait_until="domcontentloaded", timeout=60000)

        # 2. Esperar explícitamente a que el componente del visor se monte
        print("[*] Esperando a que cargue el visor PDF...")
        try:
            await page.wait_for_selector("ngx-extended-pdf-viewer, canvas", timeout=30000)
            await page.wait_for_timeout(3000) # Pausa técnica para permitir renderizado
        except Exception:
            print("[!] No se detectó el elemento del visor a tiempo. Verifica si la sesión expiró.")

        # Si capturamos los bytes vía red
        if pdf_bytes:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"[✓] PDF guardado con éxito desde la red en: {output_path}")
            await browser.close()
            return

        # 3. Inyección directa en la API de PDF.js (Estrategia recomendada para ngx-extended-pdf-viewer)
        print("[*] Extrayendo PDF directamente desde la memoria JS (PDFViewerApplication)...")
        try:
            pdf_data = await page.evaluate("""
                async () => {
                    if (window.PDFViewerApplication && window.PDFViewerApplication.pdfDocument) {
                        const data = await window.PDFViewerApplication.pdfDocument.getData();
                        return Array.from(data);
                    }
                    return null;
                }
            """)
            
            if pdf_data:
                with open(output_path, "wb") as f:
                    f.write(bytes(pdf_data))
                print(f"[✓] PDF extraído desde la memoria en: {output_path}")
            else:
                print("[X] No se encontró el objeto PDFViewerApplication en memoria. Es posible que el visor esté dentro de un iframe o requiera interacción manual.")
        except Exception as js_err:
            print(f"[X] Error al evaluar JS: {js_err}")

        await browser.close()

if __name__ == "__main__":
    url_target = "https://conoce-aqui.sunarp.gob.pe/conoce-aqui/servicio/busqueda/visualizar-partida"
    asyncio.run(descargar_pdf_desde_visor(url_target, "D:/descargas_externas/sunarp_0200-jp-2051-IE.pdf"))