
import os
import glob

print("=" * 90)
print("LOCATING ALL HTDAM v2.0 ARTIFACTS")
print("=" * 90)

# List all files in current directory
all_files = os.listdir('.')

# Filter for relevant artifacts
artifacts = {
    'reports': [],
    'charts': [],
    'data_exports': [],
    'code_samples': [],
    'specifications': []
}

# Categorize files
for f in all_files:
    if f.endswith('.md'):
        if 'BarTech' in f or 'HTDAM' in f or 'Sync' in f or 'Signal' in f or 'Transform' in f or 'Gap' in f or 'CSV' in f:
            artifacts['reports'].append(f)
        elif 'Specification' in f or 'PRD' in f:
            artifacts['specifications'].append(f)
    elif f.endswith('.png') or f.endswith('.jpg'):
        artifacts['charts'].append(f)
    elif f.endswith('.csv') and 'BarTech' in f:
        artifacts['data_exports'].append(f)
    elif f.endswith('.py') or f.endswith('.ipynb'):
        artifacts['code_samples'].append(f)

print("\nARTIFACT INVENTORY:")
print("\n1. REPORTS & DOCUMENTATION")
for f in sorted(artifacts['reports']):
    size = os.path.getsize(f) if os.path.exists(f) else 0
    print(f"   ✓ {f} ({size:,} bytes)")

print("\n2. CHARTS & VISUALIZATIONS")
for f in sorted(artifacts['charts']):
    size = os.path.getsize(f) if os.path.exists(f) else 0
    print(f"   ✓ {f} ({size:,} bytes)")

print("\n3. SPECIFICATIONS")
for f in sorted(artifacts['specifications']):
    size = os.path.getsize(f) if os.path.exists(f) else 0
    print(f"   ✓ {f} ({size:,} bytes)")

print("\n4. DATA EXPORTS")
for f in sorted(artifacts['data_exports']):
    size = os.path.getsize(f) if os.path.exists(f) else 0
    print(f"   ✓ {f} ({size:,} bytes)")

print("\n5. CODE SAMPLES")
for f in sorted(artifacts['code_samples']):
    size = os.path.getsize(f) if os.path.exists(f) else 0
    print(f"   ✓ {f} ({size:,} bytes)")

total = sum(len(v) for v in artifacts.values())
print(f"\nTOTAL ARTIFACTS: {total}")
