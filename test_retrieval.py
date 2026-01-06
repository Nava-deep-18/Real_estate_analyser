import pandas as pd
from rag.retrieval import retrieve_properties

def test_retrieval():
    print("Testing Dynamic Retrieval...")
    
    # Test 1: Location not previously hardcoded
    query1 = "Show me properties in Garia"
    res1 = retrieve_properties("FILTER", query1)
    print(f"\nQuery: '{query1}'")
    if not res1.empty and "garia" in res1.iloc[0]["Address"].lower():
        print("✅ PASS: Found Garia property")
    else:
        print(f"❌ FAIL: Returned {len(res1)} rows. First Address: {res1.iloc[0]['Address'] if not res1.empty else 'None'}")

    # Test 2: Bedroom parsing
    query2 = "3 bedroom flats"
    res2 = retrieve_properties("FILTER", query2)
    print(f"\nQuery: '{query2}'")
    if not res2.empty and res2.iloc[0]["Bedrooms"] == 3:
        print("✅ PASS: Found 3 BHK")
    else:
        print(f"❌ FAIL: Returned {len(res2)} rows. First Bed: {res2.iloc[0]['Bedrooms'] if not res2.empty else 'None'}")

    # Test 3: Complex Combo (that might fail if logic is weak)
    query3 = "2 bhk in New Town"
    res3 = retrieve_properties("FILTER", query3)
    print(f"\nQuery: '{query3}'")
    passed = True
    if res3.empty:
        print("❌ FAIL: No results")
        passed = False
    else:
        addr = res3.iloc[0]["Address"].lower()
        bed = res3.iloc[0]["Bedrooms"]
        if "new town" not in addr:
            print(f"❌ FAIL: Address mismatch ({addr})")
            passed = False
        if bed != 2:
            print(f"❌ FAIL: Bedroom mismatch ({bed})")
            passed = False
    
    if passed:
        print("✅ PASS: Found 2 BHK in New Town")

    # Test 4: COMPARE intent (Requires wealth_difference)
    query4 = "Compare buying vs renting"
    res4 = retrieve_properties("COMPARE", query4)
    print(f"\nQuery: '{query4}'")
    if not res4.empty and "wealth_difference" in res4.columns:
        print("✅ PASS: COMPARE intent returned results with wealth_difference sorted")
    else:
        print("❌ FAIL: COMPARE intent failed or missing column")

    # Test 5: EDUCATIONAL intent
    query5 = "Explain tax benefits"
    res5 = retrieve_properties("EDUCATIONAL", query5)
    print(f"\nQuery: '{query5}'")
    if not res5.empty:
        print("✅ PASS: EDUCATIONAL intent returned example context")
    else:
        print("❌ FAIL: EDUCATIONAL intent returned empty")

if __name__ == "__main__":
    test_retrieval()
