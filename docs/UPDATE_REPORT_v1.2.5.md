# GlanceWatch v1.2.5 Update Report
**Date:** April 13, 2026  
**Current Version:** 1.2.4  
**Proposed Version:** 1.2.5

---

## 📊 Current Stats
| Metric | Value |
|--------|-------|
| GitHub Stars | 3 |
| Forks | 0 |
| Open Issues | 1 (#1: Add screenshots to documentation) |
| PyPI Downloads | ~6,000+ |

---

## 🔄 Dependency Updates Required

| Package | Current Min | Latest | Action |
|---------|-------------|--------|--------|
| **FastAPI** | >=0.109.0 | 0.135.3 | ⬆️ Update to >=0.115.0 |
| **uvicorn** | >=0.27.0 | 0.44.0 | ⬆️ Update to >=0.30.0 |
| **httpx** | >=0.26.0 | 0.28.1 | ✅ OK (minor update available) |
| **pydantic** | >=2.5.0 | 2.12.5 | ⬆️ Update to >=2.10.0 |
| **pydantic-settings** | >=2.1.0 | 2.13.1 | ⬆️ Update to >=2.10.0 |
| **PyYAML** | >=6.0.1 | 6.0.3 | ✅ OK (latest) |

### Recommended `requirements.txt`:
```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
pydantic>=2.10.0
pydantic-settings>=2.10.0
PyYAML>=6.0.1
glances>=4.0.0
```

---

## 🐛 Issues Found

### 1. **UI Version Mismatch** (Critical)
- **File:** `app/ui/index.html` line 25
- **Problem:** Shows "GlanceWatch v1.0.9" - should be "v1.2.4"
- **Fix:** Update footer version string

### 2. **FastAPI Badge Outdated** (Minor)
- **File:** `README.md` line 4
- **Problem:** Shows "FastAPI-0.109+" but we support much newer
- **Fix:** Update badge to "FastAPI-0.115+"

### 3. **Coverage Badge Outdated** (Minor)
- **File:** `README.md` line 9
- **Problem:** Shows 78% coverage, but we improved to 84%
- **Fix:** Update badge to 84%

---

## 🎨 UI Improvement Suggestions

### A. **Current UI Analysis**
The current UI is functional with:
- ✅ Dark/Light mode toggle
- ✅ Circular metric cards
- ✅ Responsive grid layout
- ✅ Pulse animation for critical status

### B. **Suggested Improvements for v1.2.5**

#### 1. **Add Real-Time Charts** (High Priority)
```
- Add sparkline mini-charts showing last 30 data points
- Libraries: Chart.js or lightweight ApexCharts
- Show trends for CPU, RAM, Disk over time
```

#### 2. **Add System Info Panel** (Medium Priority)
```
- Hostname
- OS Version
- Uptime
- Python/Glances versions
```

#### 3. **Add Notification Sound Option** (Low Priority)
```
- Optional audio alert when metrics go critical
- Toggle in settings
```

#### 4. **Add Export/Share Feature** (Medium Priority)
```
- Export current metrics as JSON
- Copy shareable status link
```

#### 5. **Improve Mobile Experience** (High Priority)
```
- Larger touch targets
- Swipeable cards
- Bottom navigation for mobile
```

#### 6. **Add Metric History** (Medium Priority)
```
- Store last 24 hours of metrics in localStorage
- Show min/max/avg for the day
```

---

## 📝 Medium Article Discrepancies

**Article:** "GlanceWatch: A Lightweight Bridge Between Glances and Uptime Kuma"  
**Published:** November 12, 2025

### Items to Update in Medium Article:

1. **Version Reference**
   - Article likely shows v1.0.x or v1.2.x
   - Should mention v1.2.4 (current) or v1.2.5 (upcoming)

2. **Installation Commands**
   - Verify `curl` install script URL is correct
   - Verify all package manager commands work

3. **Port Number**
   - Ensure article shows port 8000 (not 8765)

4. **Features List**
   - Add any new features since November 2025:
     - PyPI downloads badge
     - Improved install script
     - Better test coverage

5. **Screenshots**
   - May need updated screenshots of new UI

### Recommendation:
Write a follow-up article "GlanceWatch 6 Months Later: What's New" or update the existing article with an "Updated April 2026" section.

---

## 🚀 Proposed Changes for v1.2.5

### Priority 1 (Must Have)
- [ ] Update all dependency versions in requirements.txt
- [ ] Fix UI version string (v1.0.9 → v1.2.5)
- [ ] Update README badges (FastAPI, Coverage)
- [ ] Run full test suite

### Priority 2 (Should Have)
- [ ] Add system info panel to UI
- [ ] Add sparkline charts for metrics
- [ ] Update Medium article

### Priority 3 (Nice to Have)
- [ ] Add screenshots to documentation (Issue #1)
- [ ] Add metric history to localStorage
- [ ] Mobile UI improvements

---

## 📋 Release Checklist for v1.2.5

```bash
# 1. Create feature branch
git checkout -b feature/v1.2.5-updates

# 2. Update dependencies
# Edit requirements.txt and pyproject.toml

# 3. Fix UI version
# Edit app/ui/index.html

# 4. Update badges
# Edit README.md

# 5. Run tests
pytest --cov=app tests/

# 6. Bump version
# Edit app/__init__.py, pyproject.toml, npm-package/package.json, glancewatch.rb

# 7. Commit and push
git add -A && git commit -m "chore: release v1.2.5"

# 8. Merge and tag
git checkout develop && git merge feature/v1.2.5-updates
git tag -a v1.2.5 -m "Release v1.2.5"

# 9. Deploy
python3 -m build && python3 -m twine upload dist/*
cd npm-package && npm publish --otp=XXXXXX
```

---

## Summary

**Total Issues Found:** 3 critical, 2 minor  
**Dependency Updates:** 4 packages need updating  
**UI Improvements:** 6 suggestions  
**Estimated Effort:** 2-3 hours for basic release, 1-2 days for full UI improvements
