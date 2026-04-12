from intelligence_engine import engine

def test_google_scraping():
    # Test with a candidate that likely doesn't have a Wikipedia page but has a Google presence
    # For example, a niche company name or a specific local persona
    query = "Reconsphere OSINT Tool features"
    print(f"Testing Google Intelligence for: '{query}'...")
    
    report = engine.get_identity_report(query)
    
    print("\n[REPORT RESULTS]")
    print(f"Name: {report.get('name')}")
    print(f"Source: {report.get('source')}")
    print(f"Type: {report.get('type')}")
    print(f"Summary: {report.get('description')}")
    print(f"URL: {report.get('url')}")

if __name__ == "__main__":
    test_google_scraping()
