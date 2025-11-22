# Cómo vigilar el bot (modo fácil)

Imagina que el bot es un carrito que empujamos y lo dejamos rodar. Solo hay que mirar tres luces para saber cómo va:

1. **Terminal** (la ventana donde pusiste `python app/runner.py`)
   - Si ves mensajes `INFO` cada cierto tiempo, el bot sigue vivo.
   - Si apareciera `ERROR`, saca una captura y me la mandas.
   - No cierres esta ventana, es como desenchufar el carrito.

2. **CHANGELOG (`docs/CHANGELOG.md`)**
   - Cada trade añade una nota. Si ves una nueva línea como “Trade LONG cerrado…”, significa que hizo una operación.
   - Si pasa mucho rato y no hay notas nuevas, probablemente el mercado está quieto (normal).

3. **Excel automáticos (`docs/spreadsheets/...`)**
   - Después de cada trade, los números cambian solos.
   - Solo abre los archivos cuando el bot no esté escribiendo (espera unos segundos después de ver un trade en el changelog).

### “¿El bot está activo?”
Sí, mientras la ventana de la terminal esté abierta y aparezcan mensajes cada pocos segundos.

### “¿Qué hago si veo un error?”
1. No te asustes: el bot se detiene solo.
2. Copia el mensaje exacto o toma captura.
3. Ciérralo con `Ctrl+C` y avísame para arreglarlo.

### “¿Cómo lo vuelvo a encender?”
1. Abre una terminal nueva.
2. Ve a la carpeta del proyecto (Scalp V0).
3. Escribe `python app/runner.py` y deja la ventana abierta.

Listo: con estas tres cosas sabes si el bot respira, si operó y cuánto ganó/perdió, sin entrar en detalles complicados.***
