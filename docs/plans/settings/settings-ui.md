---
description: Settings UI - schema-driven interface for viewing and editing settings
related: [settings-manager.md, ../folder-layout.md]
---

# Settings UI Design

The Settings UI is a **consumer** of the SettingsManager that dynamically builds user interfaces from registered schemas. It's decoupled from specific modules - it simply renders whatever namespaces are registered.

## Design Goals

1. **Schema-Driven**: UI is generated entirely from SettingField schemas
2. **Framework-Agnostic Core**: Logic separated from Qt/CLI/Web rendering
3. **Hierarchical Display**: Namespaces become sections/tabs, groups become subsections
4. **Provider Sub-Settings**: When selecting a provider (e.g., STT backend), show its specific settings
5. **Real-Time Validation**: Validate input as user types
6. **Secrets Indication**: Show which fields are secrets (without revealing values)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Settings UI                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐    ┌──────────────────────────────────────┐   │
│  │  SettingsViewModel   │◄───│  SettingsManager                     │   │
│  │  (Framework-agnostic)│    │  (From settings-manager.md)          │   │
│  └──────────────────────┘    └──────────────────────────────────────┘   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────┐                                               │
│  │  Renderers           │                                               │
│  │  ├── QtRenderer      │  (existing SchemaSettingsWidget)              │
│  │  ├── CLIRenderer     │  (rich/textual based)                         │
│  │  └── WebRenderer     │  (future: for Hub frontend)                   │
│  └──────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
ai-pc-spoke/src/strawberry/
├── shared/
│   └── settings/
│       └── view_model.py        # SettingsViewModel (logic layer)
├── ui/
│   ├── qt/
│   │   └── widgets/
│   │       └── settings/
│   │           ├── settings_dialog.py    # Main settings window
│   │           ├── namespace_widget.py   # Renders one namespace
│   │           ├── schema_widget.py      # Auto-renders from schema (existing)
│   │           └── provider_widget.py    # Handles provider selection + sub-settings
│   └── cli/
│       └── settings_menu.py     # CLI settings interface
```

---

## SettingsViewModel

The ViewModel is framework-agnostic logic that any renderer can use.

```python
# shared/settings/view_model.py
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .manager import SettingsManager, RegisteredNamespace
from .schema import SettingField, FieldType


@dataclass
class SettingsSection:
    """A section in the settings UI (corresponds to a namespace)."""
    namespace: str
    display_name: str
    groups: Dict[str, List[SettingField]]  # group_name -> fields
    values: Dict[str, Any]
    order: int


@dataclass
class ProviderSection:
    """A provider selection with its sub-settings."""
    parent_namespace: str      # e.g., "voice_core"
    provider_field: SettingField  # The field that selects the provider
    provider_key: str          # e.g., "stt.backend"
    available_providers: List[str]
    selected_provider: str
    provider_settings_namespace: str  # e.g., "voice.stt.whisper"


class SettingsViewModel:
    """View model for settings UI.
    
    Provides a structured view of settings organized for UI rendering.
    Handles the logic of provider selection and sub-settings.
    
    Usage:
        vm = SettingsViewModel(settings_manager)
        
        # Get sections for tabs/accordion
        sections = vm.get_sections()
        
        # Get provider sections (STT, TTS with their backends)
        providers = vm.get_provider_sections("voice_core")
        
        # Update a value
        vm.set_value("spoke_core", "hub.url", "https://...")
        
        # Listen for external changes
        vm.on_refresh(lambda: render_ui())
    """
    
    def __init__(self, settings_manager: SettingsManager):
        self._settings = settings_manager
        self._refresh_callbacks: List[Callable[[], None]] = []
        
        # Listen for changes from other sources
        self._settings.on_change(self._on_external_change)
    
    # ─────────────────────────────────────────────────────────────────
    # Sections (for main tabs/accordion)
    # ─────────────────────────────────────────────────────────────────
    
    def get_sections(self, include_provider_children: bool = False) -> List[SettingsSection]:
        """Get all settings sections for rendering.
        
        Args:
            include_provider_children: If False, excludes provider sub-namespaces
                                       (e.g., voice.stt.whisper) since they're
                                       rendered inline with their parent
        
        Returns:
            List of SettingsSection sorted by order
        """
        sections = []
        
        for ns in self._settings.get_namespaces():
            # Skip provider sub-namespaces unless requested
            if not include_provider_children and self._is_provider_namespace(ns.name):
                continue
            
            section = SettingsSection(
                namespace=ns.name,
                display_name=ns.display_name,
                groups=self._group_fields(ns.schema),
                values=self._settings.get_all(ns.name),
                order=ns.order,
            )
            sections.append(section)
        
        return sorted(sections, key=lambda s: s.order)
    
    def get_section(self, namespace: str) -> Optional[SettingsSection]:
        """Get a single section by namespace."""
        namespaces = self._settings.get_namespaces()
        ns = next((n for n in namespaces if n.name == namespace), None)
        if not ns:
            return None
        
        return SettingsSection(
            namespace=ns.name,
            display_name=ns.display_name,
            groups=self._group_fields(ns.schema),
            values=self._settings.get_all(ns.name),
            order=ns.order,
        )
    
    def _is_provider_namespace(self, namespace: str) -> bool:
        """Check if namespace is a provider sub-namespace.
        
        Provider namespaces look like: voice.stt.whisper, voice.tts.orca
        """
        parts = namespace.split(".")
        return len(parts) >= 3 and parts[0] == "voice"
    
    def _group_fields(self, schema: List[SettingField]) -> Dict[str, List[SettingField]]:
        """Group fields by their group attribute."""
        groups: Dict[str, List[SettingField]] = {}
        for field in schema:
            if field.group not in groups:
                groups[field.group] = []
            groups[field.group].append(field)
        return groups
    
    # ─────────────────────────────────────────────────────────────────
    # Provider Sections (STT/TTS with sub-settings)
    # ─────────────────────────────────────────────────────────────────
    
    def get_provider_sections(self, namespace: str) -> List[ProviderSection]:
        """Get provider selection sections for a namespace.
        
        This identifies fields that select a provider (e.g., stt.backend)
        and pairs them with the selected provider's settings namespace.
        
        Args:
            namespace: The parent namespace (e.g., "voice_core")
        
        Returns:
            List of ProviderSection for each provider selector in the namespace
        """
        sections = []
        schema = self._settings.get_schema(namespace)
        values = self._settings.get_all(namespace)
        
        # Find provider selection patterns
        provider_patterns = self._find_provider_patterns(namespace, schema, values)
        
        for pattern in provider_patterns:
            sections.append(pattern)
        
        return sections
    
    def _find_provider_patterns(
        self,
        namespace: str,
        schema: List[SettingField],
        values: Dict[str, Any],
    ) -> List[ProviderSection]:
        """Find fields that select providers with sub-settings.
        
        Looks for patterns like:
        - Field "stt.order" contains "whisper,leopard,google"
        - Namespace "voice.stt.whisper" exists
        - This is a provider pattern
        """
        patterns = []
        
        # Check for fallback order fields
        for field in schema:
            if field.key.endswith(".order"):
                # Extract provider type (e.g., "stt" from "stt.order")
                provider_type = field.key.rsplit(".", 1)[0]
                
                # Get the order value and extract first provider
                order_value = values.get(field.key, field.default) or ""
                providers = [p.strip() for p in order_value.split(",") if p.strip()]
                
                if not providers:
                    continue
                
                # Find available providers by checking registered namespaces
                available = self._get_available_providers(provider_type)
                
                # The "selected" provider is the first in the order
                selected = providers[0] if providers else ""
                provider_ns = f"voice.{provider_type}.{selected}"
                
                patterns.append(ProviderSection(
                    parent_namespace=namespace,
                    provider_field=field,
                    provider_key=field.key,
                    available_providers=available,
                    selected_provider=selected,
                    provider_settings_namespace=provider_ns,
                ))
        
        return patterns
    
    def _get_available_providers(self, provider_type: str) -> List[str]:
        """Get available providers for a type (stt, tts, etc.)."""
        providers = []
        prefix = f"voice.{provider_type}."
        
        for ns in self._settings.get_namespaces():
            if ns.name.startswith(prefix):
                provider_name = ns.name[len(prefix):]
                providers.append(provider_name)
        
        return providers
    
    def get_provider_settings(self, provider_type: str, provider_name: str) -> Optional[SettingsSection]:
        """Get the settings section for a specific provider.
        
        Args:
            provider_type: "stt", "tts", "vad", "wakeword"
            provider_name: "whisper", "leopard", "orca", etc.
        
        Returns:
            SettingsSection for the provider or None
        """
        namespace = f"voice.{provider_type}.{provider_name}"
        return self.get_section(namespace)
    
    # ─────────────────────────────────────────────────────────────────
    # Values
    # ─────────────────────────────────────────────────────────────────
    
    def get_value(self, namespace: str, key: str) -> Any:
        """Get a setting value."""
        return self._settings.get(namespace, key)
    
    def set_value(self, namespace: str, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings.set(namespace, key, value)
    
    def get_options(self, provider_name: str) -> List[str]:
        """Get dynamic options for a DYNAMIC_SELECT field."""
        return self._settings.get_options(provider_name)
    
    # ─────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────
    
    def validate_field(self, namespace: str, key: str, value: Any) -> Optional[str]:
        """Validate a field value.
        
        Args:
            namespace: The namespace
            key: The field key
            value: The value to validate
        
        Returns:
            Error message if invalid, None if valid
        """
        field = self._settings.get_field(namespace, key)
        if not field:
            return None
        
        # Run custom validation if provided
        if field.validation:
            try:
                if not field.validation(value):
                    return f"Invalid value for {field.label}"
            except Exception as e:
                return str(e)
        
        # Type validation
        if field.type == FieldType.NUMBER:
            try:
                float(value)
            except (TypeError, ValueError):
                return f"{field.label} must be a number"
        
        if field.type == FieldType.SELECT and field.options:
            if value not in field.options:
                return f"{field.label} must be one of: {', '.join(field.options)}"
        
        return None
    
    # ─────────────────────────────────────────────────────────────────
    # Events
    # ─────────────────────────────────────────────────────────────────
    
    def on_refresh(self, callback: Callable[[], None]) -> None:
        """Register callback for when UI should refresh."""
        self._refresh_callbacks.append(callback)
    
    def _on_external_change(self, namespace: str, key: str, value: Any) -> None:
        """Handle changes from outside the UI."""
        for callback in self._refresh_callbacks:
            try:
                callback()
            except Exception:
                pass
```

---

## Qt Implementation

### Main Settings Dialog

```python
# ui/qt/widgets/settings/settings_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox,
    QScrollArea, QWidget,
)

from strawberry.shared.settings import SettingsManager, SettingsViewModel
from .namespace_widget import NamespaceSettingsWidget


class SettingsDialog(QDialog):
    """Main settings dialog with tabs for each namespace."""
    
    def __init__(
        self,
        settings_manager: SettingsManager,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(700, 500)
        
        self._settings = settings_manager
        self._view_model = SettingsViewModel(settings_manager)
        
        self._setup_ui()
        self._view_model.on_refresh(self._refresh)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for sections
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # Populate tabs
        self._populate_tabs()
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _populate_tabs(self):
        """Create a tab for each settings section."""
        self._tabs.clear()
        
        for section in self._view_model.get_sections():
            # Create scrollable widget for this section
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            
            widget = NamespaceSettingsWidget(
                view_model=self._view_model,
                namespace=section.namespace,
            )
            scroll.setWidget(widget)
            
            self._tabs.addTab(scroll, section.display_name)
    
    def _refresh(self):
        """Refresh the UI when settings change externally."""
        current_tab = self._tabs.currentIndex()
        self._populate_tabs()
        if current_tab < self._tabs.count():
            self._tabs.setCurrentIndex(current_tab)
```

### Namespace Widget

```python
# ui/qt/widgets/settings/namespace_widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel,
)

from strawberry.shared.settings import SettingsViewModel
from .schema_widget import SchemaFieldWidget
from .provider_widget import ProviderSettingsWidget


class NamespaceSettingsWidget(QWidget):
    """Widget that renders all settings for a namespace."""
    
    def __init__(
        self,
        view_model: SettingsViewModel,
        namespace: str,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self._view_model = view_model
        self._namespace = namespace
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        section = self._view_model.get_section(self._namespace)
        if not section:
            layout.addWidget(QLabel("No settings available"))
            return
        
        # Render groups
        for group_name, fields in section.groups.items():
            group_box = QGroupBox(self._format_group_name(group_name))
            group_layout = QFormLayout(group_box)
            
            for field in fields:
                # Skip fields handled by provider widgets
                if field.key.endswith(".order"):
                    continue
                
                widget = SchemaFieldWidget(
                    field=field,
                    value=section.values.get(field.key),
                    options_provider=self._view_model.get_options,
                    on_change=lambda k, v: self._on_field_change(k, v),
                )
                
                label = QLabel(field.label + ":")
                if field.description:
                    label.setToolTip(field.description)
                
                group_layout.addRow(label, widget)
            
            layout.addWidget(group_box)
        
        # Render provider sections (STT, TTS, etc.)
        provider_sections = self._view_model.get_provider_sections(self._namespace)
        for ps in provider_sections:
            widget = ProviderSettingsWidget(
                view_model=self._view_model,
                provider_section=ps,
            )
            layout.addWidget(widget)
        
        layout.addStretch()
    
    def _format_group_name(self, name: str) -> str:
        """Format group name for display."""
        return name.replace("_", " ").title()
    
    def _on_field_change(self, key: str, value):
        """Handle field value changes."""
        self._view_model.set_value(self._namespace, key, value)
```

### Provider Settings Widget

```python
# ui/qt/widgets/settings/provider_widget.py
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QLabel, QFrame,
)

from strawberry.shared.settings import SettingsViewModel, ProviderSection
from .schema_widget import SchemaFieldWidget


class ProviderSettingsWidget(QWidget):
    """Widget for selecting a provider and showing its settings.
    
    Shows:
    - Dropdown to select/reorder providers
    - Inline settings for the selected provider
    """
    
    provider_changed = Signal(str)  # New provider name
    
    def __init__(
        self,
        view_model: SettingsViewModel,
        provider_section: ProviderSection,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self._view_model = view_model
        self._section = provider_section
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main group box
        provider_type = self._section.provider_field.key.split(".")[0].upper()
        group_box = QGroupBox(f"{provider_type} Provider")
        group_layout = QVBoxLayout(group_box)
        
        # Provider selection row
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Provider:"))
        
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(self._section.available_providers)
        if self._section.selected_provider:
            self._provider_combo.setCurrentText(self._section.selected_provider)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        select_layout.addWidget(self._provider_combo)
        select_layout.addStretch()
        
        group_layout.addLayout(select_layout)
        
        # Provider-specific settings (indented frame)
        self._settings_frame = QFrame()
        self._settings_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self._settings_layout = QVBoxLayout(self._settings_frame)
        self._settings_layout.setContentsMargins(20, 10, 10, 10)
        
        self._populate_provider_settings()
        
        group_layout.addWidget(self._settings_frame)
        layout.addWidget(group_box)
    
    def _populate_provider_settings(self):
        """Populate the settings frame with current provider's settings."""
        # Clear existing
        while self._settings_layout.count():
            item = self._settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get provider settings
        provider_type = self._section.provider_field.key.split(".")[0]
        provider_name = self._provider_combo.currentText()
        
        section = self._view_model.get_provider_settings(provider_type, provider_name)
        
        if not section or not section.groups:
            self._settings_layout.addWidget(QLabel("No additional settings"))
            return
        
        # Render provider settings
        from PySide6.QtWidgets import QFormLayout
        
        for group_name, fields in section.groups.items():
            form = QFormLayout()
            
            for field in fields:
                widget = SchemaFieldWidget(
                    field=field,
                    value=section.values.get(field.key),
                    options_provider=self._view_model.get_options,
                    on_change=lambda k, v, ns=section.namespace: self._on_provider_field_change(ns, k, v),
                )
                
                label = QLabel(field.label + ":")
                if field.description:
                    label.setToolTip(field.description)
                
                # Show lock icon for secrets
                if field.secret:
                    label.setText("🔒 " + label.text())
                
                form.addRow(label, widget)
            
            self._settings_layout.addLayout(form)
    
    def _on_provider_changed(self, provider_name: str):
        """Handle provider selection change."""
        # Update the fallback order - put selected provider first
        provider_type = self._section.provider_field.key.split(".")[0]
        current_order = self._view_model.get_value(
            self._section.parent_namespace,
            self._section.provider_key,
        ) or ""
        
        # Parse current order, move selected to front
        providers = [p.strip() for p in current_order.split(",") if p.strip()]
        if provider_name in providers:
            providers.remove(provider_name)
        providers.insert(0, provider_name)
        
        new_order = ",".join(providers)
        self._view_model.set_value(
            self._section.parent_namespace,
            self._section.provider_key,
            new_order,
        )
        
        # Refresh provider settings
        self._populate_provider_settings()
        self.provider_changed.emit(provider_name)
    
    def _on_provider_field_change(self, namespace: str, key: str, value):
        """Handle provider setting changes."""
        self._view_model.set_value(namespace, key, value)
```

### Schema Field Widget

```python
# ui/qt/widgets/settings/schema_widget.py
from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import (
    QWidget, QLineEdit, QCheckBox, QComboBox, QSpinBox,
    QDoubleSpinBox, QPushButton, QHBoxLayout,
)

from strawberry.shared.settings import SettingField, FieldType


class SchemaFieldWidget(QWidget):
    """Widget that renders a single SettingField."""
    
    def __init__(
        self,
        field: SettingField,
        value: Any = None,
        options_provider: Optional[Callable[[str], List[str]]] = None,
        on_change: Optional[Callable[[str, Any], None]] = None,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self._field = field
        self._value = value if value is not None else field.default
        self._options_provider = options_provider
        self._on_change = on_change
        
        self._inner_widget: QWidget = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._inner_widget = self._create_widget()
        if self._inner_widget:
            layout.addWidget(self._inner_widget)
    
    def _create_widget(self) -> Optional[QWidget]:
        """Create the appropriate widget for the field type."""
        field = self._field
        value = self._value
        
        if field.type == FieldType.TEXT:
            widget = QLineEdit()
            widget.setText(str(value) if value else "")
            widget.textChanged.connect(self._emit_change)
            return widget
        
        elif field.type == FieldType.PASSWORD:
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.EchoMode.Password)
            widget.setText(str(value) if value else "")
            widget.setPlaceholderText("••••••••" if value else "Enter value...")
            widget.textChanged.connect(self._emit_change)
            return widget
        
        elif field.type == FieldType.NUMBER:
            if isinstance(field.default, float):
                widget = QDoubleSpinBox()
                widget.setRange(-999999, 999999)
                widget.setDecimals(2)
                widget.setValue(float(value) if value else 0.0)
                widget.valueChanged.connect(self._emit_change)
            else:
                widget = QSpinBox()
                widget.setRange(-999999, 999999)
                widget.setValue(int(value) if value else 0)
                widget.valueChanged.connect(self._emit_change)
            return widget
        
        elif field.type == FieldType.CHECKBOX:
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.stateChanged.connect(lambda s: self._emit_change(bool(s)))
            return widget
        
        elif field.type == FieldType.SELECT:
            widget = QComboBox()
            if field.options:
                widget.addItems(field.options)
                if value in field.options:
                    widget.setCurrentText(str(value))
            widget.currentTextChanged.connect(self._emit_change)
            return widget
        
        elif field.type == FieldType.DYNAMIC_SELECT:
            widget = QComboBox()
            if self._options_provider and field.options_provider:
                try:
                    options = self._options_provider(field.options_provider)
                    widget.addItems(options)
                    if value and str(value) in options:
                        widget.setCurrentText(str(value))
                except Exception:
                    if value:
                        widget.addItem(str(value))
            widget.currentTextChanged.connect(self._emit_change)
            return widget
        
        elif field.type == FieldType.ACTION:
            widget = QPushButton(field.label)
            widget.clicked.connect(lambda: self._emit_action())
            return widget
        
        return None
    
    def _emit_change(self, value: Any):
        """Emit value change."""
        if self._on_change:
            self._on_change(self._field.key, value)
    
    def _emit_action(self):
        """Emit action trigger."""
        if self._on_change and self._field.action:
            self._on_change(f"__action__{self._field.action}", True)
    
    def get_value(self) -> Any:
        """Get the current widget value."""
        widget = self._inner_widget
        
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        
        return None
    
    def set_value(self, value: Any):
        """Set the widget value without triggering change event."""
        widget = self._inner_widget
        
        if isinstance(widget, QLineEdit):
            widget.blockSignals(True)
            widget.setText(str(value) if value else "")
            widget.blockSignals(False)
        elif isinstance(widget, QCheckBox):
            widget.blockSignals(True)
            widget.setChecked(bool(value))
            widget.blockSignals(False)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.blockSignals(True)
            widget.setValue(value if value else 0)
            widget.blockSignals(False)
        elif isinstance(widget, QComboBox):
            widget.blockSignals(True)
            if widget.findText(str(value)) >= 0:
                widget.setCurrentText(str(value))
            widget.blockSignals(False)
```

---

## UI Layout Examples

### Main Settings Dialog

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Settings                                                           [X]  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Spoke Core] [Voice] [Skills]                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ General ──────────────────────────────────────────────────────────┐ │
│  │ Device Name:    [My PC                         ]                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Hub ──────────────────────────────────────────────────────────────┐ │
│  │ Hub URL:        [https://hub.example.com       ]                   │ │
│  │ 🔒 Hub Token:   [••••••••                      ]                   │ │
│  │                 [Connect to Hub]                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Offline ──────────────────────────────────────────────────────────┐ │
│  │ Offline Model:  [▼ llama3.2:3b                 ]                   │ │
│  │ Enable Offline: [✓]                                                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                              [Cancel]  [OK]             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Voice Tab with Provider Settings

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Settings                                                           [X]  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Spoke Core] [Voice] [Skills]                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ STT Provider ─────────────────────────────────────────────────────┐ │
│  │ Provider:     [▼ leopard                      ]                    │ │
│  │ ┌───────────────────────────────────────────────────────────────┐  │ │
│  │ │ 🔒 Access Key:  [••••••••                   ]                 │  │ │
│  │ └───────────────────────────────────────────────────────────────┘  │ │
│  │ Fallback Order: [leopard,whisper,google       ]                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ TTS Provider ─────────────────────────────────────────────────────┐ │
│  │ Provider:     [▼ orca                         ]                    │ │
│  │ ┌───────────────────────────────────────────────────────────────┐  │ │
│  │ │ 🔒 Access Key:  [••••••••                   ]                 │  │ │
│  │ │ Voice:         [▼ female                    ]                 │  │ │
│  │ └───────────────────────────────────────────────────────────────┘  │ │
│  │ Fallback Order: [orca,piper,google            ]                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Wake Word ────────────────────────────────────────────────────────┐ │
│  │ Phrase:        [hey strawberry                ]                    │ │
│  │ Enabled:       [✓]                                                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                              [Cancel]  [OK]             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## CLI Implementation

For CLI-based settings (using Rich or Textual):

```python
# ui/cli/settings_menu.py
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from strawberry.shared.settings import SettingsManager, SettingsViewModel, FieldType


class CLISettingsMenu:
    """CLI settings interface using Rich."""
    
    def __init__(self, settings_manager: SettingsManager):
        self._settings = settings_manager
        self._view_model = SettingsViewModel(settings_manager)
        self._console = Console()
    
    def show(self):
        """Show the settings menu."""
        while True:
            self._console.clear()
            self._show_sections_menu()
            
            choice = Prompt.ask(
                "Select section (or 'q' to quit)",
                default="q",
            )
            
            if choice.lower() == "q":
                break
            
            sections = self._view_model.get_sections()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sections):
                    self._show_section(sections[idx])
            except ValueError:
                pass
    
    def _show_sections_menu(self):
        """Display available settings sections."""
        table = Table(title="Settings Sections")
        table.add_column("#", style="cyan")
        table.add_column("Section", style="green")
        
        for i, section in enumerate(self._view_model.get_sections(), 1):
            table.add_row(str(i), section.display_name)
        
        self._console.print(table)
    
    def _show_section(self, section):
        """Display and edit settings for a section."""
        while True:
            self._console.clear()
            self._console.print(Panel(section.display_name, style="bold blue"))
            
            # List all settings
            all_fields = []
            for group_name, fields in section.groups.items():
                self._console.print(f"\n[bold]{group_name.title()}[/bold]")
                for field in fields:
                    value = section.values.get(field.key, field.default)
                    display_value = "••••••••" if field.secret and value else str(value)
                    all_fields.append(field)
                    idx = len(all_fields)
                    self._console.print(f"  {idx}. {field.label}: {display_value}")
            
            self._console.print("\n")
            choice = Prompt.ask(
                "Select setting to edit (or 'b' to go back)",
                default="b",
            )
            
            if choice.lower() == "b":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(all_fields):
                    self._edit_field(section.namespace, all_fields[idx])
                    # Refresh section data
                    section = self._view_model.get_section(section.namespace)
            except ValueError:
                pass
    
    def _edit_field(self, namespace: str, field):
        """Edit a single field."""
        current = self._view_model.get_value(namespace, field.key)
        
        if field.type == FieldType.CHECKBOX:
            new_value = Confirm.ask(
                f"{field.label}",
                default=bool(current),
            )
        elif field.type == FieldType.SELECT and field.options:
            self._console.print(f"\nOptions: {', '.join(field.options)}")
            new_value = Prompt.ask(
                field.label,
                default=str(current) if current else "",
            )
        else:
            new_value = Prompt.ask(
                field.label,
                default=str(current) if current else "",
                password=field.type == FieldType.PASSWORD,
            )
        
        self._view_model.set_value(namespace, field.key, new_value)
        self._console.print(f"[green]Updated {field.label}[/green]")
```

---

## Implementation Steps

1. [ ] Create `shared/settings/view_model.py`
2. [ ] Create `ui/qt/widgets/settings/` directory structure
3. [ ] Implement `SettingsDialog` (main window)
4. [ ] Implement `NamespaceSettingsWidget`
5. [ ] Implement `ProviderSettingsWidget`
6. [ ] Refactor existing `SchemaSettingsWidget` to `SchemaFieldWidget`
7. [ ] Implement `CLISettingsMenu` (optional, lower priority)
8. [ ] Wire up settings dialog in main Qt app
9. [ ] Add tests for SettingsViewModel
10. [ ] Update existing settings dialogs to use new system

---

## Related Documents

- [settings-manager.md](./settings-manager.md) - SettingsManager backend
- [../folder-layout.md](../folder-layout.md) - Overall folder structure
- [../settings-design.md](../settings-design.md) - Original design sketch
