# Tools Directory

This directory contains utility scripts and tools for managing the GATE exam integration and other project tasks.

## 📁 Available Tools

### 🔽 **download_gate_pdfs.py**
Automated GATE PDF downloader that fetches question papers from the official website.

**Features:**
- Downloads all 30 GATE streams across 5 years (2021-2025)
- Intelligent URL pattern detection
- Proper file naming convention
- Resume capability (skips existing files)
- Progress tracking and error reporting

**Usage:**
```bash
# Download all available GATE PDFs
python tools/download_gate_pdfs.py

# List existing downloaded files
python tools/download_gate_pdfs.py --list

# Show help
python tools/download_gate_pdfs.py --help
```

**Output:** Files saved to `data_pipeline/source_pdfs/GATE/` with naming format `GATE-YYYY-STREAM-Session-N.pdf`

---

### 🔗 **gate_urls_extractor.py**
URL repository and accessibility checker for GATE PDFs.

**Features:**
- Complete URL database for all GATE streams and years
- URL pattern analysis
- Accessibility testing
- Stream-specific and year-specific URL lookup

**Usage:**
```bash
# Show URL summary
python tools/gate_urls_extractor.py

# Check which URLs are accessible
python tools/gate_urls_extractor.py --check

# Get URLs for specific stream
python tools/gate_urls_extractor.py --stream CS

# Get URLs for specific year
python tools/gate_urls_extractor.py --year 2025
```

---

### 🧪 **test_gate_download.py**
Lightweight testing tool for download functionality.

**Features:**
- Tests URL patterns without full downloads
- Sample download testing
- Quick accessibility checks
- Cleanup utilities

**Usage:**
```bash
# Test URL patterns only
python tools/test_gate_download.py

# Test patterns + sample downloads
python tools/test_gate_download.py --download

# Clean up test files
python tools/test_gate_download.py --cleanup
```

---

### 🧪 **gate_integration_test.py**
Comprehensive integration testing suite.

**Features:**
- Tests entire GATE pipeline (PDFs → Parsing → Vector DB → AI Generation)
- Modular test execution
- Detailed reporting
- Compatibility verification

**Usage:**
```bash
# Run all integration tests
python tools/gate_integration_test.py

# Quick tests only
python tools/gate_integration_test.py --quick

# Test parsing pipeline only
python tools/gate_integration_test.py --parsing

# Test AI generation only
python tools/gate_integration_test.py --generation
```

## 🚀 Common Workflows

### **Fresh GATE Setup**
```bash
# 1. Download GATE PDFs
python tools/download_gate_pdfs.py

# 2. Parse PDFs to JSON
uv run python -m data_pipeline.scripts.parse_pdfs

# 3. Build vector database
uv run python -m data_pipeline.scripts.build_vector_db

# 4. Test integration
python tools/gate_integration_test.py
```

### **Debug Download Issues**
```bash
# Check URL accessibility
python tools/gate_urls_extractor.py --check

# Test specific stream
python tools/test_gate_download.py --download

# Manual URL lookup
python tools/gate_urls_extractor.py --stream CS
```

### **Verify Integration**
```bash
# Quick health check
python tools/gate_integration_test.py --quick

# Full integration test
python tools/gate_integration_test.py
```

## 📋 Tool Dependencies

All tools are designed to work independently and have minimal dependencies:

- **Standard libraries:** `os`, `sys`, `requests`, `json`, `asyncio`
- **Project modules:** Only imported when needed, with proper error handling
- **Optional dependencies:** Tests gracefully handle missing components

## 🔧 Extending the Tools

### Adding New Exam Types
1. Update URL patterns in `gate_urls_extractor.py`
2. Modify download logic in `download_gate_pdfs.py`
3. Add test cases in `gate_integration_test.py`

### Adding New Download Sources
1. Create new URL pattern functions
2. Update `download_gate_pdfs.py` with new base URLs
3. Test with `test_gate_download.py`

## 📝 Notes

- Tools are designed to be **idempotent** - safe to run multiple times
- All tools include **comprehensive error handling** and **helpful output**
- **State-aware** - tools detect existing work and avoid duplication
- **Modular design** - each tool can be used independently or as part of pipeline

## 🆘 Troubleshooting

### Common Issues

**HTTP 403 Errors:**
- Some years (2022-2024) may have access restrictions
- Use `gate_urls_extractor.py --check` to verify current status

**Download Failures:**
- Check internet connection
- Verify URL patterns haven't changed
- Use `test_gate_download.py` for debugging

**Integration Test Failures:**
- Ensure PDFs are downloaded first
- Run parsing and vector DB scripts
- Check that all dependencies are installed

**API Key Errors (in generation tests):**
- Set `GEMINI_API_KEY` environment variable
- Generation tests will show warnings but continue without API key
