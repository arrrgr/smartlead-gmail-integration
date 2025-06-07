#!/usr/bin/env python3
"""Run analysis with predefined credentials"""

from analyze_missing_messages import analyze_smartlead_data, compare_with_upload_log

# Your credentials
API_KEY = "eefa0acd-633f-4734-bbd3-46ac9f4d2f6b_9ma6p68"
CLIENT_ID = "38760"
UPLOADED_COUNT = 1670
EXPECTED_COUNT = 2858

print("Running Smartlead analysis...")
print("="*60)

# Run the analysis
results = analyze_smartlead_data(API_KEY, CLIENT_ID)

# Compare with what was uploaded
compare_with_upload_log(results['total_messages'], UPLOADED_COUNT)

# Show difference from expected
print(f"\nDifference from your expected count ({EXPECTED_COUNT}): {EXPECTED_COUNT - results['total_messages']} messages")
print(f"\nMessages in Smartlead but not uploaded: {results['total_messages'] - UPLOADED_COUNT}") 