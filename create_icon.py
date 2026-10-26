"""
Script para crear un icono simple para MUSHYRA
Creador: MushhX
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent

def create_mushyra_icon():
    """Crear icono de MUSHYRA"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError('Instala las dependencias con: python -m pip install ".[build]"') from exc
    
    # Tamaños de icono estándar
    sizes = [16, 32, 48, 64, 128, 256]
    
    # Crear imagen base (256x256)
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colores
    bg_color = (41, 128, 185)  # Azul
    text_color = (255, 255, 255)  # Blanco
    
    # Dibujar círculo de fondo
    margin = 10
    draw.ellipse([margin, margin, size-margin, size-margin], fill=bg_color)
    
    # Dibujar texto "M"
    try:
        # Intentar usar fuente del sistema
        font_size = int(size * 0.6)
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        # Usar fuente por defecto
        font = ImageFont.load_default()
    
    text = "M"
    
    # Calcular posición centrada
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10
    
    # Dibujar texto
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Guardar como PNG
    img.save(ROOT / 'mux_icon.png', 'PNG')
    print("✅ Icono PNG creado: mux_icon.png")
    
    # Intentar crear ICO
    try:
        img.save(ROOT / 'mux_icon.ico', format='ICO', sizes=[(s, s) for s in sizes])
        print("✅ Icono ICO creado: mux_icon.ico")
    except Exception as e:
        print(f"⚠️ No se pudo crear ICO: {e}")
        print("   Puedes convertir mux_icon.png a ICO manualmente")

if __name__ == '__main__':
    create_mushyra_icon()


# Alias interno para scripts que aún importan el nombre anterior.
create_mux_icon = create_mushyra_icon
