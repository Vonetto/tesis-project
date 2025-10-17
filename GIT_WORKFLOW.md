# Git Workflow - Tesis Project

## 🌿 Arquitectura de Ramas

```
main (producción estable)
  ↓
develop (desarrollo activo)
  ├─ feature/*  → nuevas funcionalidades
  └─ docs/*     → documentación, paper, tesis
```

---

## 📋 Ramas Principales

### `main` - Producción Estable
- **Propósito:** Código estable y validado, hitos importantes
- **Protección:** No hacer commits directos, solo merges desde `develop`
- **Tagging:** Usar tags para versiones importantes
  ```bash
  git tag -a v0.1-bronze-complete -m "Bronze layer complete and validated"
  git tag -a v0.2-silver-ready -m "Silver layer with geographic enrichment"
  git tag -a v0.3-gold-metrics -m "Gold layer with inertia metrics"
  git tag -a v1.0-pre-defense -m "Version for thesis defense"
  ```

### `develop` - Desarrollo Activo
- **Propósito:** Integración continua, trabajo día a día
- **Libertad:** Puede estar temporalmente "roto" mientras trabajas
- **Flujo:** 
  ```bash
  git checkout develop
  # Hacer cambios y commits frecuentes
  git add .
  git commit -m "feat(scope): description"
  ```

---

## 🔧 Ramas de Soporte (Temporales)

### `feature/*` - Nuevas Funcionalidades

**Cuándo crear:**
- Implementación de módulos grandes
- Cambios que toman varios días
- Experimentación que puede fallar

**Ejemplos:**
- `feature/gold-inertia-metrics` → Métricas de entropía, HHI, RCS
- `feature/spatial-analysis` → Análisis espacial avanzado con GeoPandas
- `feature/temporal-segmentation` → Segmentación por patrones temporales
- `feature/user-panel-pipeline` → Pipeline de agregación usuario-semana

**Workflow:**
```bash
# Crear desde develop
git checkout develop
git pull origin develop
git checkout -b feature/gold-inertia-metrics

# Trabajar...
git add lib/metrics.py
git commit -m "feat(gold): implement Shannon entropy for route diversity"

# Al terminar: merge a develop
git checkout develop
git merge feature/gold-inertia-metrics --no-ff
git branch -d feature/gold-inertia-metrics  # Eliminar rama local
```

### `docs/*` - Documentación y Paper

**Cuándo crear:**
- Escribir capítulos de la tesis
- Desarrollar el paper académico
- Crear presentaciones de defensa
- Documentación metodológica extensa

**Ejemplos:**
- `docs/paper-draft` → Borrador del paper para conferencia/journal
- `docs/thesis-chapter-2-data` → Capítulo de datos y metodología
- `docs/thesis-chapter-3-analysis` → Capítulo de análisis y resultados
- `docs/defense-slides` → Presentación de defensa
- `docs/methodology-inertia` → Documentación de métricas de inercia

**Workflow:**
```bash
# Crear desde develop
git checkout develop
git checkout -b docs/paper-draft

# Trabajar en el paper
mkdir -p docs/paper
git add docs/paper/paper.tex
git commit -m "docs(paper): add introduction and literature review"

# Commits incrementales
git commit -m "docs(paper): add methodology section"
git commit -m "docs(paper): add results and discussion"

# Al terminar: merge a develop
git checkout develop
git merge docs/paper-draft --no-ff

# Mantener la rama para futuras revisiones (NO borrar)
```

---

## 📝 Convención de Commits (Conventional Commits)

### Formato
```
<tipo>(<scope>): <descripción corta>

<descripción larga opcional>
<referencias opcionales>
```

### Tipos
- `feat:` - Nueva funcionalidad
- `fix:` - Corrección de bugs
- `refactor:` - Refactorización sin cambio de funcionalidad
- `docs:` - Documentación
- `style:` - Formato, estilo (sin cambio de lógica)
- `test:` - Tests
- `chore:` - Tareas de mantenimiento
- `perf:` - Mejoras de performance
- `analysis:` - Análisis exploratorio o resultados

### Scopes Comunes
- `pipeline` - Scripts de ingesta/procesamiento
- `bronze` - Capa Bronze del Data Lake
- `silver` - Capa Silver del Data Lake
- `gold` - Capa Gold del Data Lake
- `eda` - Notebooks de EDA
- `setup` - Configuración y validación
- `lib` - Utilidades compartidas
- `paper` - Paper académico
- `thesis` - Documento de tesis
- `metrics` - Implementación de métricas

### Ejemplos
```bash
# Funcionalidad nueva
git commit -m "feat(silver): implement geographic enrichment with Zonas777 joins"

# Corrección de bug
git commit -m "fix(process_data): handle missing timestamps in CSV parsing"

# Refactorización
git commit -m "refactor(lib): move date parsing utils to datalake.py"

# Documentación
git commit -m "docs(readme): add data lake architecture diagram"

# Análisis
git commit -m "analysis(eda): QR users show 30% higher route diversity vs traditional"

# Performance
git commit -m "perf(silver): optimize partitioned writes using sink_parquet"
```

---

## 🔄 Workflows Comunes

### 1. Trabajo Diario en `develop`
```bash
# Empezar el día
git checkout develop
git pull origin develop

# Trabajar y commitear frecuentemente
git add <archivos>
git commit -m "tipo(scope): descripción"

# Al final del día
git push origin develop
```

### 2. Funcionalidad Grande (Feature Branch)
```bash
# Crear feature
git checkout develop
git checkout -b feature/nombre-descriptivo

# Trabajar...
git add .
git commit -m "feat(scope): descripción"

# Mantener actualizado con develop
git checkout develop
git pull origin develop
git checkout feature/nombre-descriptivo
git merge develop  # Resolver conflictos si hay

# Al terminar
git checkout develop
git merge feature/nombre-descriptivo --no-ff
git push origin develop
git branch -d feature/nombre-descriptivo
```

### 3. Escribir Documentación (Docs Branch)
```bash
# Crear rama de docs
git checkout develop
git checkout -b docs/paper-draft

# Escribir...
git add docs/
git commit -m "docs(paper): add methodology section"

# Al terminar (o checkpoints importantes)
git checkout develop
git merge docs/paper-draft --no-ff
git push origin develop
# NO borrar la rama, mantener para revisiones
```

### 4. Hito Importante: Merge a `main`
```bash
# Cuando develop está estable y quieres marcar un hito
git checkout main
git pull origin main
git merge develop --no-ff -m "Merge develop: Bronze layer complete"

# Crear tag
git tag -a v0.1-bronze-complete -m "Bronze layer validated with all weeks"

# Push
git push origin main
git push origin --tags
```

---

## 🚫 Qué NO Hacer

❌ **NO hacer commits directos a `main`**
```bash
# MAL
git checkout main
git commit -m "fix something"  # ❌
```

❌ **NO hacer force push a ramas compartidas**
```bash
# MAL
git push --force origin main    # ❌
git push --force origin develop # ❌
```

❌ **NO commitear datos sensibles o archivos grandes**
```bash
# MAL - Ya están en .gitignore, pero por si acaso:
git add *.csv        # ❌
git add *.parquet    # ❌
git add *credentials*.json  # ❌
```

❌ **NO commitear archivos generados**
```bash
# MAL - Ya están en .gitignore:
git add **/*.html     # ❌
git add _site/        # ❌
git add .quarto/      # ❌
```

---

## ✅ Checklist Antes de Merge a `main`

Antes de hacer `git merge develop` en `main`, verificar:

- [ ] Todos los notebooks ejecutan sin errores
- [ ] Los datos en Bronze/Silver están validados
- [ ] No hay credenciales ni datos sensibles commiteados
- [ ] El README está actualizado con cambios importantes
- [ ] Los commits tienen mensajes descriptivos
- [ ] No hay trabajo en progreso (WIP) sin terminar

---

## 📊 Ver Estado del Repo

```bash
# Ver ramas
git branch -a

# Ver historial gráfico
git log --oneline --graph --all --decorate

# Ver cambios pendientes
git status

# Ver diferencias
git diff

# Ver tags
git tag -l
```

---

## 🆘 Comandos de Emergencia

### Deshacer cambios locales no commiteados
```bash
git restore <archivo>    # Deshacer cambios en un archivo
git restore .           # Deshacer todos los cambios
```

### Deshacer último commit (mantener cambios)
```bash
git reset --soft HEAD~1
```

### Cambiar mensaje del último commit
```bash
git commit --amend -m "nuevo mensaje"
```

### Recuperar rama borrada accidentalmente
```bash
git reflog               # Buscar el commit
git checkout -b rama-recuperada <commit-hash>
```

---

## 📚 Recursos

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow Cheatsheet](https://danielkummer.github.io/git-flow-cheatsheet/)
- [Atlassian Git Tutorials](https://www.atlassian.com/git/tutorials)

---

**Última actualización:** Octubre 2025  
**Mantenido por:** Juan Vicente Onetto Romero

