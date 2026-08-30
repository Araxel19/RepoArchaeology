<div align="center">

# 🏛️ RepoArchaeology

### *Arqueología Forense de Repositorios · Descubre la Historia, Deuda Oculta y Linaje de tu Código*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20(Fedora%20%7C%20Ubuntu%20%7C%20Arch)-E95420?style=for-the-badge&logo=linux&logoColor=white)](https://kernel.org)
[![CLI / TUI](https://img.shields.io/badge/Interface-Rich%20CLI%20%26%20TUI-10B981?style=for-the-badge)](https://github.com/Araxel19/RepoArchaeology)

<p align="center">
  <b>RepoArchaeology</b> no es un chatbot. Es una herramienta nativa de terminal diseñada para hacer autopsias y diagnósticos profundos a cualquier repositorio Git, detectando archivos frágiles, acoplamiento invisible y explicando el <i>porqué</i> histórico de las decisiones de tu arquitectura.
</p>

</div>

---

## 🌟 ¿Qué problema resuelve?

Cuando entras a un proyecto nuevo o tu propio repositorio crece, surgen preguntas difíciles:
- ❓ *¿Qué archivos son los más peligrosos y propensos a romperse si los modifico?*
- ❓ *¿Qué módulos se modifican siempre juntos aunque no tengan `import` entre sí (Acoplamiento Fantasma)?*
- ❓ *¿Por qué se creó este archivo gigante hace 2 años y qué problema intentaba resolver originalmente?*
- ❓ *¿Quién es el referente histórico de cada parte del sistema?*

**RepoArchaeology** cruza el historial de Git, análisis de frecuencia de cambios (*code churn*), detección de parches de emergencia y análisis sintáctico (AST) para darte respuestas visuales, claras y accionables.

---

## ✨ Características Principales

| Módulo | Icono | Descripción |
| :--- | :---: | :--- |
| **Escaneo de Salud (Doctor)** | 🩺 | Calcula un puntaje de 0 a 100 de la salud histórica de tu repositorio y genera recomendaciones claras. |
| **Hotspots & Churn** | 🔥 | Identifica los puntos calientes: archivos con alta frecuencia de edición y alta tasa de errores corregidos. |
| **Acoplamiento Fantasma** | 👻 | Encuentra archivos que cambian simultáneamente en los mismos commits sin relación aparente. |
| **Linaje de Decisiones** | 📜 | Resume la evolución y contexto de un archivo o carpeta sin tener que leer 100 commits manuales. |
| **Breaking Changes Semánticos** | ⚡ | Compara dos versiones o ramas alertando cambios en firmas públicas y modelos de datos. |
| **Reportes Visuales** | 📊 | Genera reportes elegantes en la propia terminal, o exporta en Markdown interactivo y JSON. |

---

## 🚀 Instalación Rápida en Linux (Nativa)

### Opción 1: Instalador Automático (Recomendado)
Clona el repositorio y ejecuta el instalador en un solo paso:

```bash
git clone https://github.com/Araxel19/RepoArchaeology.git
cd RepoArchaeology
./install.sh
```

El instalador creará un entorno aislado seguro en `~/.local/share/repoarchaeology` y creará el comando global **`repoarch`** en tu `~/.local/bin`.

### Opción 2: Instalación Manual para Desarrollo
```bash
git clone https://github.com/Araxel19/RepoArchaeology.git
cd RepoArchaeology
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 🎮 Guía de Uso (Simple e Intuitiva)

Puedes ejecutar **`repoarch`** en cualquier carpeta que tenga un repositorio Git.

### 1. Diagnóstico Rápido de Salud
```bash
repoarch doctor
```
> Analiza los últimos 100 commits, calcula la concentración de autoría (*Bus Factor*) y detecta archivos en riesgo crítico.

### 2. Detección de Archivos Calientes (Hotspots)
```bash
repoarch churn --top 10
```
> Muestra los 10 archivos con mayor rotación de cambios y porcentaje de riesgo.

### 3. Detección de Acoplamiento Fantasma
```bash
repoarch coupling --min-confidence 0.6
```
> Descubre qué archivos tienen una fuerte correlación oculta en el historial.

### 4. Arqueología de un Archivo Específico
```bash
repoarch lore ruta/al/archivo.dart
```
> Reconstruye la historia del archivo, quiénes trabajaron en él, qué bugs solucionó y por qué existe en su forma actual.

### 5. Generación de Reporte Completo
```bash
repoarch scan --export report.md
```

---

## 🛡️ Seguridad y Privacidad por Diseño

* 🔒 **100% Local por defecto:** Todo el análisis de Git y heurísticas se ejecuta en tu máquina sin enviar datos a la nube.
* 🛡️ **Sanitización de Rutas:** Validación estricta contra ataques de *Path Traversal*.
* 🚫 **Máscara de Secretos:** Los tokens, contraseñas o claves privadas en mensajes de commit se enmascaran automáticamente (`[REDACTED_SECRET]`).
* ⚡ **Ejecución Segura:** Subprocesos con límites de tiempo (*timeouts*) estrictos y argumentos sanitizados sin `shell=True`.

---

## 🏗️ Arquitectura del Sistema

```
RepoArchaeology/
├── repoarchaeology/
│   ├── cli/              # Interfaz de comandos (Typer + Rich)
│   ├── core/             # Configuración, seguridad y modelos Pydantic
│   ├── engines/          # Motores de análisis (Git, AST, IA pluggable)
│   ├── exporters/        # Exportadores de reportes (Markdown, JSON, HTML)
│   └── tui/              # Interfaz interactiva de terminal (Textual)
├── tests/                # Suite de pruebas unitarias
├── install.sh            # Instalador nativo para Linux
└── uninstall.sh          # Desinstalador limpio
```

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Para empezar:
1. Haz un Fork del repositorio.
2. Crea una rama para tu función (`git checkout -b feature/nueva-capacidad`).
3. Realiza tus cambios y verifica las pruebas (`pytest`).
4. Abre un Pull Request detallado.

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT** — consulta el archivo [LICENSE](LICENSE) para más detalles.

Desarrollado con ❤️ por [Araxel](https://github.com/Araxel19).
