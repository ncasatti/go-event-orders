"""
Payload Navigator - Navegación jerárquica de payloads con fzf

Permite navegar interactivamente por la estructura de directorios de payloads
y descubrir payloads legacy.
"""

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

# ============================================================================
# Enums
# ============================================================================


class EntryType(Enum):
    """Tipo de entrada en el navegador de payloads."""

    FOLDER = "folder"
    FILE = "file"
    LEGACY = "legacy"
    BACK = "back"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PayloadEntry:
    """Entrada en el navegador de payloads."""

    path: Path
    display_name: str
    entry_type: EntryType
    label: Optional[str] = None


# ============================================================================
# Payload Navigator
# ============================================================================


class PayloadNavigator:
    """
    Navegador jerárquico de payloads con soporte para fzf.

    Permite descubrir y navegar payloads tanto en la nueva estructura
    composable como en ubicaciones legacy.
    """

    def __init__(self, payloads_dir: Path, legacy_dirs: Optional[List[Path]] = None):
        """
        Inicializa el navegador.

        Args:
            payloads_dir: Directorio raíz de payloads composables
            legacy_dirs: Lista de directorios legacy (opcional)
        """
        self.payloads_dir = Path(payloads_dir)
        self.legacy_dirs = legacy_dirs or []

    def discover_all(self, func_name: str) -> List[PayloadEntry]:
        """
        Descubre todos los payloads disponibles (composables + legacy).

        Args:
            func_name: Nombre de la función (para filtrar legacy)

        Returns:
            Lista de PayloadEntry
        """
        entries = []

        # Descubrir payloads composables en raíz
        if self.payloads_dir.exists():
            entries.extend(self._list_directory(self.payloads_dir))

        # Descubrir payloads legacy
        entries.extend(self._discover_legacy(func_name))

        return entries

    def navigate_with_fzf(self, func_name: str) -> Optional[Path]:
        """
        Navegación jerárquica con fzf.

        Permite navegar por carpetas y seleccionar archivos de payload.

        Args:
            func_name: Nombre de la función (para filtrar/priorizar)

        Returns:
            Path del archivo seleccionado o None si canceló
        """
        current_path = self.payloads_dir

        while True:
            items = []
            item_map = {}  # display_text -> (path, entry_type)

            # Agregar opción de volver si no estamos en raíz
            if current_path != self.payloads_dir:
                back_text = "⬅️  [BACK]  ../"
                items.append(back_text)
                item_map[back_text] = (current_path.parent, EntryType.BACK)

            # Listar contenido del directorio actual
            entries = self._list_directory(current_path)
            for entry in entries:
                items.append(entry.display_name)
                item_map[entry.display_name] = (entry.path, entry.entry_type)

            # Agregar payloads legacy si estamos en raíz
            if current_path == self.payloads_dir:
                legacy_entries = self._discover_legacy(func_name)
                for entry in legacy_entries:
                    items.append(entry.display_name)
                    item_map[entry.display_name] = (entry.path, entry.entry_type)

            # Mostrar fzf
            selected = self._show_fzf(
                items, header=f"📂 {current_path.relative_to(self.payloads_dir.parent)}"
            )

            if selected is None:
                return None  # Usuario canceló

            path, entry_type = item_map[selected]

            if entry_type in [EntryType.FOLDER, EntryType.BACK]:
                # Navegar a subdirectorio
                current_path = path
            else:
                # Archivo seleccionado
                return path

    def _list_directory(self, path: Path) -> List[PayloadEntry]:
        """
        Lista el contenido de un directorio.

        Args:
            path: Directorio a listar

        Returns:
            Lista de PayloadEntry ordenada (carpetas primero, luego archivos)
        """
        if not path.exists() or not path.is_dir():
            return []

        entries = []

        # Listar contenido
        for entry in sorted(path.iterdir()):
            # Saltar archivos que empiezan con _ (metadata, base, etc)
            if entry.name.startswith("_") and entry.is_file():
                continue

            if entry.is_dir():
                # Carpeta
                entries.append(
                    PayloadEntry(
                        path=entry,
                        display_name=f"📁 [FOLDER]  {entry.name}/",
                        entry_type=EntryType.FOLDER,
                    )
                )

            elif entry.suffix in [".yaml", ".yml", ".json"]:
                # Archivo de payload
                entries.append(
                    PayloadEntry(
                        path=entry, display_name=f"📄 {entry.name}", entry_type=EntryType.FILE
                    )
                )

        # Ordenar: carpetas primero, luego archivos
        entries.sort(key=lambda e: (e.entry_type != EntryType.FOLDER, e.path.name))

        return entries

    def _discover_legacy(self, func_name: str) -> List[PayloadEntry]:
        """
        Descubre payloads legacy en ubicaciones antiguas.

        Busca en:
        - test-payloads/ (compartidos)
        - functions/{func_name}/payloads/ (locales)

        Args:
            func_name: Nombre de la función

        Returns:
            Lista de PayloadEntry con label LEGACY/SHARED/LOCAL
        """
        entries = []

        # Buscar en test-payloads/ (compartidos)
        test_payloads_dir = Path("test-payloads")
        if test_payloads_dir.exists():
            for payload_file in sorted(test_payloads_dir.glob("*.json")):
                entries.append(
                    PayloadEntry(
                        path=payload_file,
                        display_name=f"[SHARED ]  {payload_file.name}",
                        entry_type=EntryType.LEGACY,
                        label="SHARED",
                    )
                )

        # Buscar en functions/{func_name}/payloads/ (locales)
        func_payloads_dir = Path("functions") / func_name / "payloads"
        if func_payloads_dir.exists():
            for payload_file in sorted(func_payloads_dir.glob("*.json")):
                entries.append(
                    PayloadEntry(
                        path=payload_file,
                        display_name=f"[LOCAL  ]  {payload_file.name}",
                        entry_type=EntryType.LEGACY,
                        label="LOCAL",
                    )
                )

        # Buscar en directorios legacy adicionales
        for legacy_dir in self.legacy_dirs:
            if legacy_dir.exists():
                for payload_file in sorted(legacy_dir.glob("*.json")):
                    entries.append(
                        PayloadEntry(
                            path=payload_file,
                            display_name=f"[LEGACY ]  {payload_file.name}",
                            entry_type=EntryType.LEGACY,
                            label="LEGACY",
                        )
                    )

        return entries

    def _show_fzf(self, items: List[str], header: str = "") -> Optional[str]:
        """
        Muestra fzf con las opciones dadas.

        Args:
            items: Lista de items a mostrar
            header: Header para fzf

        Returns:
            Item seleccionado o None si canceló
        """
        if not items:
            return None

        try:
            # Preparar input para fzf
            input_text = "\n".join(items)

            # Ejecutar fzf
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    "40%",
                    "--reverse",
                    "--border",
                    "--header",
                    header,
                    "--prompt",
                    "📄 Select payload: ",
                    "--preview-window",
                    "hidden",  # Sin preview por ahora
                ],
                input=input_text,
                text=True,
                capture_output=True,
                check=False,
            )

            # fzf retorna 0 si seleccionó, 130 si canceló (Ctrl+C)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None

        except FileNotFoundError:
            # fzf no está instalado
            raise RuntimeError(
                "fzf is not installed. Install it with:\n"
                "  Ubuntu/Debian: sudo apt install fzf\n"
                "  macOS: brew install fzf\n"
                "  Arch: sudo pacman -S fzf"
            )
        except Exception as e:
            raise RuntimeError(f"Error running fzf: {e}")
