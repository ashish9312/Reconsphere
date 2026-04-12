from intelligence_engine import engine

def test_intel():
    print("Testing identification for 'Shah Rukh Khan'...")
    report = engine.get_identity_report("Shah Rukh Khan")
    print(f"Name: {report['name']}")
    print(f"Source: {report['source']}")
    print(f"Summary: {report['description'][:100]}...")
    
    print("\nTesting normalization for 'ananya_panday.jpg'...")
    norm = engine.normalize_name("ananya_panday.jpg")
    print(f"Normalized: {norm}")
    
    print("\nTesting unverified identity for 'Unknown Random Person 123'...")
    report2 = engine.get_identity_report("Unknown Random Person 123")
    print(f"Name: {report2['name']}")
    print(f"Source: {report2['source']}")

if __name__ == "__main__":
    test_intel()
