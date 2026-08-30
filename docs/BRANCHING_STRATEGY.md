# 🏛️ Estrategia de Ramas en RepoArchaeology

Este documento describe la asignación actual de ramas creadas en el repositorio y los objetivos técnicos de cada una:

## 📌 Ramas Actuales

### 1. `main`
* **Estado:** Estable / Inicial (v0.1.0).
* **Contenido:** Arquitectura base, motor Git, CLI con Typer/Rich, instalador nativo y seguridad.

### 2. `develop`
* **Estado:** Rama activa por defecto para nuevas integraciones.
* **Objetivo:** Recibir los avances de las ramas de características antes de consolidar la versión `v0.2.0`.

### 3. `feature/tui-dashboard`
* **Objetivo:** Construir la interfaz de terminal interactiva (TUI) a pantalla completa con [Textual](https://textual.textualize.io/).
* **Hitos:**
  - Navegador interactivo de archivos y hotspots con gráficos ASCII en vivo.
  - Pestaña de inspección de acoplamientos con filtros por confianza.
  - Visor interactivo de linaje de archivos con scroll.

### 4. `feature/ast-treesitter`
* **Objetivo:** Integrar análisis de sintaxis estática multi-lenguaje (Python, Dart, TypeScript, Rust, Go).
* **Hitos:**
  - Detección de cambios a nivel de funciones y clases (no solo líneas de texto).
  - Identificación automática de *Breaking Changes* en firmas públicas de APIs.

### 5. `feature/ai-connectors`
* **Objetivo:** Implementar los conectores locales y en la nube opcionales.
* **Hitos:**
  - Integración nativa con Ollama local (`qwen2.5-coder`, `llama3.1`).
  - Conector para Google Gemini API y OpenAI con Structured Outputs (JSON Schema).
