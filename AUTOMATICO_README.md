# GameFlash — noticias automáticas

Esta versión mantiene la web estática: no necesita Node.js, localhost ni un servidor propio.

## Cómo funciona
- `news.json` contiene las noticias que muestra la web.
- `scripts/fetch_news.py` busca noticias gaming mediante feeds RSS públicos y obtiene la imagen de la noticia cuando está disponible.
- Si la página no ofrece imagen, usa una imagen de respaldo del juego.
- GitHub Actions ejecuta el script cada hora y guarda los cambios.
- Si Netlify está conectado al repositorio de GitHub, cada cambio publicado vuelve a desplegar GameFlash automáticamente.

## Activarlo
1. Crea un repositorio en GitHub.
2. Sube TODO el contenido de esta carpeta.
3. En GitHub, entra en Actions y ejecuta `Actualizar noticias GameFlash` una vez con `Run workflow`.
4. Conecta ese repositorio a Netlify (si todavía no lo tienes conectado).
5. A partir de ahí, el workflow se ejecutará cada hora.

No hace falta crear claves API.

## Importante
Las noticias y sus imágenes pertenecen a sus fuentes originales. GameFlash enlaza a la noticia original. Revisa los derechos de uso de imágenes antes de publicar el sitio públicamente.
