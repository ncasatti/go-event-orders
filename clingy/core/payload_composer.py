"""
Payload Composer - Sistema de composición de payloads YAML/JSON

Permite componer payloads Lambda desde múltiples archivos base con merge profundo.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ============================================================================
# Constants
# ============================================================================

MAX_MERGE_DEPTH = 10

REQUIRED_LAMBDA_FIELDS = ["version", "routeKey", "rawPath"]

RECOMMENDED_FIELDS = ["requestContext", "headers"]


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ComposedPayload:
    """Resultado de la composición de un payload."""

    data: dict
    sources: List[Path]
    warnings: List[str]


@dataclass
class ValidationResult:
    """Resultado de la validación de un payload."""

    valid: bool
    errors: List[str]
    warnings: List[str]


# ============================================================================
# Exceptions
# ============================================================================


class PayloadError(Exception):
    """Error durante la composición o validación de payloads."""

    pass


# ============================================================================
# Payload Composer
# ============================================================================


class PayloadComposer:
    """
    Compositor de payloads con soporte para merge profundo.

    Permite componer payloads Lambda desde múltiples archivos base
    siguiendo un orden de precedencia definido.
    """

    def __init__(self, payloads_dir: Path):
        """
        Inicializa el compositor.

        Args:
            payloads_dir: Directorio raíz de payloads
        """
        self.payloads_dir = Path(payloads_dir)
        self.base_dir = self.payloads_dir / "_base"

    def deep_merge(self, base: dict, override: dict, depth: int = 0) -> dict:
        """
        Merge recursivo donde override tiene prioridad.

        Reglas:
        1. Si ambos valores son dict → merge recursivo
        2. Si ambos valores son list → override reemplaza (no concatena)
        3. Cualquier otro caso → override reemplaza
        4. Keys en override que no existen en base → se agregan
        5. Keys en base que no existen en override → se mantienen
        6. Si override es None → eliminar la key

        Args:
            base: Diccionario base
            override: Diccionario que sobreescribe
            depth: Profundidad actual (para detectar ciclos)

        Returns:
            Diccionario mergeado

        Raises:
            PayloadError: Si se excede la profundidad máxima
        """
        if depth > MAX_MERGE_DEPTH:
            raise PayloadError(
                f"Max merge depth ({MAX_MERGE_DEPTH}) exceeded. "
                "Possible circular reference or overly nested structure."
            )

        result = base.copy()

        for key, override_value in override.items():
            if key in result:
                base_value = result[key]

                # Si override es None, eliminar la key
                if override_value is None:
                    del result[key]
                    continue

                # Si base es None, usar override directamente
                if base_value is None:
                    result[key] = override_value
                    continue

                # Caso 1: Ambos son dict → merge recursivo
                if isinstance(base_value, dict) and isinstance(override_value, dict):
                    result[key] = self.deep_merge(base_value, override_value, depth + 1)

                # Caso 2 y 3: Override reemplaza
                else:
                    result[key] = override_value
            else:
                # Caso 4: Key nueva (solo agregar si no es None)
                if override_value is not None:
                    result[key] = override_value

        return result

    def load_yaml_safe(self, path: Path) -> dict:
        """
        Carga YAML con manejo de errores detallado.

        Args:
            path: Ruta al archivo YAML

        Returns:
            Diccionario con el contenido del archivo

        Raises:
            PayloadError: Si el archivo no existe, tiene sintaxis inválida,
                         o no es un diccionario
        """
        if not YAML_AVAILABLE:
            raise PayloadError("PyYAML is not installed. Install it with: pip install pyyaml")

        if not path.exists():
            raise PayloadError(f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

                # Archivo vacío
                if data is None:
                    return {}

                # Validar que sea un diccionario
                if not isinstance(data, dict):
                    raise PayloadError(f"YAML must be a dictionary, got {type(data).__name__}")

                return data

        except yaml.YAMLError as e:
            # Extraer línea y columna del error
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                raise PayloadError(
                    f"Invalid YAML in {path.name} at line {mark.line + 1}, "
                    f"column {mark.column + 1}:\n  {e.problem}"
                )
            raise PayloadError(f"Invalid YAML in {path.name}: {e}")

    def load_json_safe(self, path: Path) -> dict:
        """
        Carga JSON con manejo de errores.

        Args:
            path: Ruta al archivo JSON

        Returns:
            Diccionario con el contenido del archivo

        Raises:
            PayloadError: Si el archivo no existe o tiene sintaxis inválida
        """
        if not path.exists():
            raise PayloadError(f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                if not isinstance(data, dict):
                    raise PayloadError(f"JSON must be a dictionary, got {type(data).__name__}")

                return data

        except json.JSONDecodeError as e:
            raise PayloadError(
                f"Invalid JSON in {path.name} at line {e.lineno}, " f"column {e.colno}: {e.msg}"
            )

    def load_file_safe(self, path: Path) -> dict:
        """
        Carga archivo YAML o JSON según extensión.

        Args:
            path: Ruta al archivo

        Returns:
            Diccionario con el contenido del archivo
        """
        if path.suffix in [".yaml", ".yml"]:
            return self.load_yaml_safe(path)
        elif path.suffix == ".json":
            return self.load_json_safe(path)
        else:
            raise PayloadError(
                f"Unsupported file format: {path.suffix}. " "Use .yaml, .yml, or .json"
            )

    def compose(self, selected_file: Path, stage: str) -> ComposedPayload:
        """
        Compone el payload final mergeando archivos en orden.

        Order of Precedence (menor a mayor prioridad):
        1. _base/general.yaml           ← Prioridad más BAJA
        2. _base/context-{stage}.yaml   ← Stage actual (dev/prod)
        3. {function}/_metadata.yaml    ← Metadata de la función
        4. Archivo seleccionado         ← Prioridad más ALTA (gana)

        Args:
            selected_file: Archivo seleccionado por usuario
            stage: Stage actual (dev/prod)

        Returns:
            ComposedPayload con data, sources y warnings
        """
        result = {}
        sources = []
        warnings = []

        # 1. Cargar base general (si existe)
        general_path = self.base_dir / "general.yaml"
        if general_path.exists():
            try:
                general_data = self.load_file_safe(general_path)
                result = self.deep_merge(result, general_data)
                sources.append(general_path)
            except PayloadError as e:
                warnings.append(f"Failed to load {general_path.name}: {e}")
        else:
            warnings.append(f"Optional base file not found: {general_path.name}")

        # 2. Cargar context del stage (si existe)
        context_path = self.base_dir / f"context-{stage}.yaml"
        if context_path.exists():
            try:
                context_data = self.load_file_safe(context_path)
                result = self.deep_merge(result, context_data)
                sources.append(context_path)
            except PayloadError as e:
                warnings.append(f"Failed to load {context_path.name}: {e}")
        else:
            # Buscar fallback
            context_files = list(self.base_dir.glob("context-*.yaml"))
            if context_files:
                fallback = context_files[0]
                warnings.append(
                    f"Context for stage '{stage}' not found. " f"Using fallback: {fallback.name}"
                )
                try:
                    fallback_data = self.load_file_safe(fallback)
                    result = self.deep_merge(result, fallback_data)
                    sources.append(fallback)
                except PayloadError as e:
                    warnings.append(f"Failed to load {fallback.name}: {e}")
            else:
                warnings.append(f"No context files found in {self.base_dir.name}/")

        # 3. Cargar metadata de función (si el archivo está en subcarpeta)
        selected_file = Path(selected_file)
        if selected_file.parent != self.payloads_dir and not selected_file.parent.name.startswith(
            "_"
        ):

            function_dir = selected_file.parent
            metadata_path = function_dir / "_metadata.yaml"

            if metadata_path.exists():
                try:
                    metadata_data = self.load_file_safe(metadata_path)
                    result = self.deep_merge(result, metadata_data)
                    sources.append(metadata_path)
                except PayloadError as e:
                    warnings.append(f"Failed to load {metadata_path.name}: {e}")
            else:
                warnings.append(
                    f"Optional metadata file not found: " f"{function_dir.name}/_metadata.yaml"
                )

        # 4. Cargar archivo seleccionado (REQUERIDO)
        try:
            selected_data = self.load_file_safe(selected_file)
            result = self.deep_merge(result, selected_data)
            sources.append(selected_file)
        except PayloadError as e:
            raise PayloadError(f"Failed to load selected file: {e}")

        return ComposedPayload(data=result, sources=sources, warnings=warnings)

    def compose_from_snippets(self, snippet_paths: List[Path], stage: str) -> ComposedPayload:
        """
        Compose payload from multiple snippet files.

        Merge order:
        1. _base/general.yaml (always)
        2. _base/context-{stage}.yaml (stage-specific)
        3. Each snippet in order (last wins on conflicts)

        Args:
            snippet_paths: List of snippet file paths in merge order
            stage: Current stage (dev/prod)

        Returns:
            ComposedPayload with merged data, sources, and warnings
        """
        result = {}
        sources = []
        warnings = []

        # 1. Load base general (if exists)
        general_path = self.base_dir / "general.yaml"
        if general_path.exists():
            try:
                general_data = self.load_file_safe(general_path)
                result = self.deep_merge(result, general_data)
                sources.append(general_path)
            except PayloadError as e:
                warnings.append(f"Failed to load {general_path.name}: {e}")
        else:
            warnings.append(f"Optional base file not found: {general_path.name}")

        # 2. Load context for stage (if exists)
        context_path = self.base_dir / f"context-{stage}.yaml"
        if context_path.exists():
            try:
                context_data = self.load_file_safe(context_path)
                result = self.deep_merge(result, context_data)
                sources.append(context_path)
            except PayloadError as e:
                warnings.append(f"Failed to load {context_path.name}: {e}")
        else:
            # Try fallback
            context_files = list(self.base_dir.glob("context-*.yaml"))
            if context_files:
                fallback = context_files[0]
                warnings.append(
                    f"Context for stage '{stage}' not found. Using fallback: {fallback.name}"
                )
                try:
                    fallback_data = self.load_file_safe(fallback)
                    result = self.deep_merge(result, fallback_data)
                    sources.append(fallback)
                except PayloadError as e:
                    warnings.append(f"Failed to load {fallback.name}: {e}")

        # 3. Merge each snippet in order
        for snippet_path in snippet_paths:
            try:
                snippet_data = self.load_file_safe(Path(snippet_path))
                result = self.deep_merge(result, snippet_data)
                sources.append(Path(snippet_path))
            except PayloadError as e:
                raise PayloadError(f"Failed to load snippet {snippet_path}: {e}")

        return ComposedPayload(data=result, sources=sources, warnings=warnings)

    def validate(self, payload: dict) -> ValidationResult:
        """
        Valida que el payload tenga estructura correcta para Lambda.

        Args:
            payload: Payload a validar

        Returns:
            ValidationResult con valid, errors y warnings
        """
        errors = []
        warnings = []

        # Campos requeridos
        for field in REQUIRED_LAMBDA_FIELDS:
            if field not in payload:
                errors.append(f"Missing required field: {field}")

        # Campos recomendados
        for field in RECOMMENDED_FIELDS:
            if field not in payload:
                warnings.append(f"Missing recommended field: {field}")

        # Validar body si existe
        if "body" in payload:
            body = payload["body"]
            if not isinstance(body, (str, dict, list, type(None))):
                errors.append(
                    f"Body must be string, dict, list, or null. " f"Got: {type(body).__name__}"
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
