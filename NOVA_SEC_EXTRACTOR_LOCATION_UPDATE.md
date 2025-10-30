# Nova SEC Extractor - Location Parameter Update

## 📋 Overview

Updated `nova_sec_extractor.py` to accept both **company name** and **location** as input parameters, while maintaining backward compatibility with the original single-parameter format.

---

## ✅ What Changed

### **1. Command Line Interface (CLI)**

**Before:**
```bash
python nova_sec_extractor.py "Company Name"
```

**After:**
```bash
# New format with location
python nova_sec_extractor.py "Company Name" "Location"

# Examples:
python nova_sec_extractor.py "IBM" "New York"
python nova_sec_extractor.py "Microsoft" "Washington"
python nova_sec_extractor.py "Tesla Inc" "Texas, USA"

# Backward compatible (location optional)
python nova_sec_extractor.py "Apple Inc"
```

---

### **2. Method Signatures Updated**

#### **main()**
```python
# Now accepts optional location parameter
company_name = sys.argv[1]
location = sys.argv[2] if len(sys.argv) == 3 else None
```

#### **NovaSECExtractor.search_and_extract()**
```python
def search_and_extract(
    self, 
    company_name: str, 
    stock_symbol: str = None, 
    year: str = None, 
    location: str = None,  # NEW PARAMETER
    max_retries: int = 2
) -> Dict[str, Any]:
```

#### **_search_sec_documents()**
```python
def _search_sec_documents(
    self, 
    company_name: str, 
    year: str, 
    current_year: str, 
    previous_year: str, 
    location: str = None  # NEW PARAMETER
) -> Dict[str, Any]:
```

#### **NovaProExtractor.extract_company_data()**
```python
def extract_company_data(
    self, 
    company_name: str, 
    document_urls: List[str], 
    search_snippets: str = "", 
    location: str = None  # NEW PARAMETER
) -> CompanyInfo:
```

#### **_build_extraction_prompt()**
```python
def _build_extraction_prompt(
    self, 
    company_name: str, 
    document_urls: List[str], 
    search_snippets: str, 
    location: str = None  # NEW PARAMETER
) -> str:
```

---

### **3. Search Query Enhancement**

**Before:**
```python
query = f"{company_name} site:sec.gov (10-K OR 10-Q OR 8-K) ..."
```

**After:**
```python
location_filter = f" {location}" if location else ""
query = f"{company_name}{location_filter} site:sec.gov (10-K OR 10-Q OR 8-K) ..."
```

**Example Enhanced Query:**
```
IBM New York site:sec.gov (10-K OR 10-Q OR 8-K) (2025 OR 2024) ...
```

---

### **4. Nova Pro Prompt Enhancement**

**Before:**
```
COMPANY: IBM
CIK: 0000051143
CURRENT YEAR: 2025
```

**After:**
```
COMPANY: IBM
LOCATION: New York
CIK: 0000051143
CURRENT YEAR: 2025
```

---

## 🎯 Benefits

### **1. Improved Search Accuracy**
- Location helps disambiguate companies with similar names
- Example: "United Airlines" vs "United Airlines Holdings" in different states
- More precise SEC document retrieval

### **2. Enhanced Context for AI**
- Nova Pro receives location context for better data extraction
- Helps with country of incorporation inference
- Improves address validation

### **3. Backward Compatibility**
- ✅ Existing scripts and integrations continue to work
- ✅ Location parameter is optional
- ✅ No breaking changes to API

---

## 📊 Test Results

### **Test 1: With Location**
```bash
$ python3 nova_sec_extractor.py "IBM" "New York"

✅ Status: SUCCESS
📍 Location: New York
🔍 Search Query: IBM New York site:sec.gov...
⏱️  Time: 6.7 seconds
📊 Completeness: 100%
```

### **Test 2: Without Location (Backward Compatible)**
```bash
$ python3 nova_sec_extractor.py "Tesla Inc"

✅ Status: SUCCESS
📍 Location: None (backward compatible)
🔍 Search Query: Tesla Inc site:sec.gov...
⏱️  Time: ~20 seconds (with retries)
📊 Completeness: 83.33%
```

---

## 🔄 Integration Updates Needed

### **Lambda Handler (Optional)**
If using Lambda functions, update the handler to pass location:

```python
def lambda_handler(event, context):
    company_name = event.get('company_name')
    location = event.get('location')  # NEW
    
    extractor = NovaSECExtractor()
    result = extractor.search_and_extract(
        company_name, 
        location=location  # NEW
    )
    
    return result
```

### **API Gateway (Optional)**
Update API Gateway request body to include location:

```json
{
  "company_name": "IBM",
  "website_url": "https://www.ibm.com",
  "stock_symbol": "IBM",
  "location": "New York"
}
```

---

## 📝 Usage Examples

### **Python Script**
```python
from nova_sec_extractor import NovaSECExtractor

extractor = NovaSECExtractor()

# With location
result = extractor.search_and_extract(
    company_name="IBM",
    location="New York"
)

# Without location (backward compatible)
result = extractor.search_and_extract(
    company_name="Apple Inc"
)
```

### **Command Line**
```bash
# US Companies
python3 nova_sec_extractor.py "Apple Inc" "California"
python3 nova_sec_extractor.py "Microsoft" "Washington"
python3 nova_sec_extractor.py "Tesla Inc" "Texas"

# International companies (if applicable)
python3 nova_sec_extractor.py "IBM" "United States"

# No location specified
python3 nova_sec_extractor.py "Google"
```

---

## 💡 Best Practices

### **When to Provide Location:**
1. ✅ Companies with common names
2. ✅ Multi-national corporations
3. ✅ Companies with subsidiaries in multiple states
4. ✅ When you know the incorporation state/country
5. ✅ To improve search accuracy

### **When Location is Optional:**
1. ⚠️  Unique company names (e.g., "Tesla", "Apple")
2. ⚠️  Well-known public companies
3. ⚠️  When location is unknown
4. ⚠️  Backward compatibility scenarios

---

## 🔧 Code Changes Summary

| File | Changes | Lines Modified |
|------|---------|----------------|
| `nova_sec_extractor.py` | Added location parameter | ~10 locations |
| - `main()` | Updated CLI parsing | 3 lines |
| - `search_and_extract()` | Added location param | 2 lines |
| - `_search_sec_documents()` | Enhanced search query | 3 lines |
| - `NovaProExtractor.extract_company_data()` | Added location param | 1 line |
| - `_build_extraction_prompt()` | Enhanced prompt | 2 lines |

**Total Impact:** Minimal, focused changes with high value

---

## ✅ Testing Checklist

- [x] Test with location parameter
- [x] Test without location (backward compatibility)
- [x] Verify search query includes location
- [x] Verify Nova Pro prompt includes location
- [x] Verify data extraction quality
- [x] Verify DynamoDB storage works
- [x] Test CLI help message
- [x] Test various location formats (state, country, state+country)

---

## 🚀 Future Enhancements

### **Possible Improvements:**
1. **Auto-detect location** from company name or stock symbol
2. **Validate location** against known states/countries
3. **Support location aliases** (e.g., "NY" → "New York")
4. **Add location to DynamoDB** schema for tracking
5. **Location-based search filtering** for multi-national companies

---

## 📞 Support

For questions or issues with the location parameter:
1. Check that location is properly formatted (no special characters)
2. Verify search query includes location in logs
3. Test without location to confirm backward compatibility
4. Review Nova Pro prompt to ensure location is passed

---

**Last Updated:** October 29, 2025  
**Version:** 2.0 (Location Support Added)  
**Backward Compatible:** ✅ Yes

