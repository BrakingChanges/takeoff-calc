""" Simple script to calculate takeoff thrust """

print("Loading Data...")

from main import find_n1, create_interpolator
import pandas as pd

# Read the data from the CSV file

derates = {
    'TO': 'data-26K.csv',
    'TO-1': 'data-24K.csv',
    'TO-2': 'data-22K.csv'
}

df_in = pd.read_csv(derates[input('Derate')])

# Create an interpolation function for N1
df_in.columns = ['Assumed Temperature (C)', 'Airport Pressure Altitude (ft)',
                 'N1 (%)', 'Minimum Assumed Temperature (C)']

# Example usage
press_altitude_in = int(input('Enter pressure altitude'))
assumed_temp_in = int(input('Enter assumed temp'))
n1 = find_n1(press_altitude_in, assumed_temp_in, create_interpolator(df_in))

print(f'Interpolated N1: {n1} %')
