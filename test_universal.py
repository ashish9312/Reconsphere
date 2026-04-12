from intelligence_engine import engine
import time

def test_universal_intelligence():
    # Test cases
    subjects = [
        "Shah Rukh Khan",      # Test Wikipedia Priority
        "ReconSphere OSINT",   # Test Google/DDG Fallback
        "NicheEntityXYZ123"    # Test Local Fallback (likely no results)
    ]
    
    for subject in subjects:
        print(f"\n--- Testing Intelligence for: '{subject}' ---")
        start_time = time.time()
        report = engine.get_identity_report(subject)
        duration = time.time() - start_time
        
        print(f"Name:     {report.get('name')}")
        print(f"Source:   {report.get('source')} (found in {duration:.2f}s)")
        print(f"Type:     {report.get('type')}")
        print(f"Summary:  {report.get('description')[:150]}...")
        if report.get('url'):
            print(f"Link:     {report.get('url')}")

if __name__ == "__main__":
    test_universal_intelligence()
