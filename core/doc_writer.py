from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

DOCS_DIR = Path("docs")
CHANGELOG_PATH = DOCS_DIR / "CHANGELOG.md"
CAPABILITIES_PATH = DOCS_DIR / "CAPABILITIES.md"

CHANGELOG_HEADER = "# Scalp V0 – CHANGELOG\nHistorial de cambios del bot, generado automáticamente.\n\n"
CAPABILITIES_HEADER = "# Scalp V0 – Current Capabilities\n\n"


def _ensure_docs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if not CHANGELOG_PATH.exists():
        CHANGELOG_PATH.write_text(CHANGELOG_HEADER, encoding="utf-8")
    if not CAPABILITIES_PATH.exists():
        CAPABILITIES_PATH.write_text(CAPABILITIES_HEADER, encoding="utf-8")


def append_changelog(entry: Dict[str, str]) -> None:
    """Añade una nueva entrada al changelog sin interrumpir el bot por errores de escritura."""
    try:
        _ensure_docs()
        content = (
            f"## [{entry.get('timestamp', datetime.utcnow().isoformat())}] – {entry.get('type', 'UPDATE')}\n"
            f"### Módulo:\n{entry.get('module', 'desconocido')}\n"
            f"### Descripción:\n{entry.get('description', '').strip()}\n"
            f"### Versión:\n{entry.get('version', '0.0.1')}\n\n"
        )
        with CHANGELOG_PATH.open("a", encoding="utf-8") as f:
            f.write(content)
    except Exception as exc:  # pragma: no cover - solo registro
        logger.warning("No se pudo escribir en CHANGELOG.md: %s", exc)


def update_capabilities(info: Dict[str, List[str]]) -> None:
    """Actualiza el documento de capacidades manteniendo el encabezado intacto."""
    try:
        _ensure_docs()
        sections: List[str] = []
        for key, items in info.items():
            title = _format_section_title(key)
            body = "\n".join(f"- {item}" for item in items)
            sections.append(f"## {title}\n{body}\n")
        content = CAPABILITIES_HEADER + "\n".join(sections)
        CAPABILITIES_PATH.write_text(content, encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        logger.warning("No se pudo actualizar CAPABILITIES.md: %s", exc)


def _format_section_title(raw: str) -> str:
    mapping = {
        "datos_mercado": "Datos de mercado",
        "estrategia": "Estrategia",
        "riesgo": "Gestión de riesgo",
        "estados": "Estados",
        "ejecucion": "Ejecución",
        "stats": "Estadísticas",
    }
    return mapping.get(raw, raw.replace("_", " ").title())

