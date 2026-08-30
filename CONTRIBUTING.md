# 🌿 Guía de Contribución y Organización de Ramas

¡Gracias por tu interés en contribuir a **RepoArchaeology**! Para mantener un desarrollo ordenado, predecible y de alta calidad, seguimos un modelo de ramas estructurado basado en **Git Flow simplificado**.

---

## 🌳 Estructura y Jerarquía de Ramas

```
main (Producción y Releases Oficiales)
  │
  └── develop (Integración Principal de Desarrollo)
        │
        ├── feature/tui-dashboard      ──> Dashboard interactivo con Textual
        ├── feature/ast-treesitter     ──> Análisis sintáctico con Tree-sitter
        ├── feature/ai-connectors      ──> Conectores de IA (Ollama / Gemini)
        │
        ├── fix/<nombre-del-bug>       ──> Correcciones de bugs no urgentes
        │
        └── hotfix/<version-critica>   ──> Parches urgentes directo hacia main
```

### 1. `main` (Rama Principal)
* Representa el código **estable, testeado y listo para producción**.
* Solo recibe código mediante Pull Requests (PR) desde `develop` o ramas `hotfix/*`.
* Cada versión aquí está etiquetada con un Git Tag semántico (ej. `v0.1.0`, `v0.2.0`).

### 2. `develop` (Integración Activa)
* Es la rama base para el trabajo diario.
* Aquí se fusionan todas las ramas de nuevas características (`feature/*`) una vez revisadas.

### 3. Ramas de Trabajo (`feature/*`, `fix/*`, `docs/*`)

| Prefijo | Propósito | Ejemplo |
| :--- | :--- | :--- |
| `feature/` | Nuevas funcionalidades o motores de análisis | `feature/tui-dashboard`, `feature/ast-treesitter` |
| `fix/` | Corrección de errores detectados en desarrollo | `fix/git-log-parser-encoding` |
| `docs/` | Mejoras en documentación, diagramas o guías | `docs/user-guide-and-examples` |
| `refactor/`| Mejoras de arquitectura sin alterar el comportamiento | `refactor/security-redaction-engine` |
| `hotfix/` | Parches críticos de emergencia para `main` | `hotfix/crash-on-empty-repo` |

---

## 📝 Convención de Commits (Conventional Commits)

Utilizamos mensajes de commit semánticos y legibles:

* `feat: ...` -> Nueva funcionalidad añadida.
* `fix: ...` -> Corrección de un error o bug.
* `docs: ...` -> Cambios exclusivos en documentación.
* `refactor: ...` -> Reestructuración de código sin alterar su funcionamiento.
* `test: ...` -> Adición o corrección de pruebas unitarias.
* `chore: ...` -> Tareas de mantenimiento, dependencias o configuración del proyecto.

**Ejemplo:**
```bash
git commit -m "feat(git_engine): add Jaccard similarity index to ghost coupling detector"
```

---

## 🚀 Flujo para Crear una Nueva Característica

1. **Sincroniza y párate en `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   ```

2. **Crea tu rama de feature:**
   ```bash
   git checkout -b feature/nombre-de-tu-mejora
   ```

3. **Haz tus cambios y verifica las pruebas:**
   ```bash
   pytest
   ```

4. **Haz commit y push:**
   ```bash
   git add .
   git commit -m "feat: descripción clara del cambio"
   git push origin feature/nombre-de-tu-mejora
   ```

5. **Abre un Pull Request hacia `develop`.**
