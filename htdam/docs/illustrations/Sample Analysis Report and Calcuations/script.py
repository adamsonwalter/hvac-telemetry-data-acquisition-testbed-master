
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load the three CSV files
chwst_df = pd.read_csv('BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv')
chwrt_df = pd.read_csv('BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv')
cdwrt_df = pd.read_csv('BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CDWRT_Entering_Condenser_Water_Temperature_Sensor.csv')

print("=" * 80)
print("TELEMETRY FILE INSPECTION")
print("=" * 80)

print(f"\nCHWST (Chilled Water Supply Temperature):")
print(f"  Shape: {chwst_df.shape}")
print(f"  Columns: {chwst_df.columns.tolist()}")
print(f"  First 5 rows:\n{chwst_df.head()}")
print(f"  Data types:\n{chwst_df.dtypes}")

print(f"\nCHWRT (Chilled Water Return Temperature):")
print(f"  Shape: {chwrt_df.shape}")
print(f"  First 5 rows:\n{chwrt_df.head()}")

print(f"\nCDWRT (Condenser Water Return Temperature):")
print(f"  Shape: {cdwrt_df.shape}")
print(f"  First 5 rows:\n{cdwrt_df.head()}")
