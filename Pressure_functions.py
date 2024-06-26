import numpy as np
import pandas as pd
from datetime import datetime
import os
import re
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

def hex_to_binary_file(filename):
    # Generate the output filename
    output_filename = f"Hex_{filename}"
    print(filename)

    try:
        with open(filename, 'r') as file:
            content = file.read()
        # content = StringIO(uploaded_file.getvalue().decode("utf-8"))    
        # Use regex to find all valid hex value pairs
        hex_values = re.findall(r'\b[0-9A-Fa-f]{2}\b', content)
        
        # Convert hex values to binary bytes
        binary_values = bytes(int(hex_val, 16) for hex_val in hex_values)

        # Write the binary values to the output file
        with open(output_filename, 'wb') as file:
            file.write(binary_values)
        
        print(f"Binary values written to {output_filename}")
    except FileNotFoundError:
        print(f"File {filename} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return hex_values

def calculate_pressure_temperature_original(D1_pres, D2_temp, C):
    temperature_divider = 9
    pressure_divider = 8
    pressure_base = 4030000
    pressure_base = 3530000 #lowered this when i used a second device and it's baseline was lower. Need to lower in the compression too.
    temperature_base = 4630000
    
    D1_pres = np.int32(np.float64(D1_pres) * (2 ** pressure_divider) + pressure_base)
    D2_temp = np.int32(np.float64(D2_temp) * (2 ** temperature_divider) + temperature_base)
    
    MS5837_30 = 1
    MS5837_02BA = 0

    C = [np.int16(c) for c in C]

    TEMP = 0
    P = 0
    model = MS5837_30
    dT = np.int32(0)
    SENS = np.int64(0)
    OFF = np.int64(0)
    SENSi = np.int32(0)
    OFFi = np.int32(0)
    Ti = np.int32(0)
    OFF2 = np.int64(0)
    SENS2 = np.int64(0)

    dT = np.int32(D2_temp) - np.int32(C[4]) * np.int32(256)

    if model == MS5837_02BA:
        SENS = np.int64(C[0]) * np.int32(65536) + (np.int64(C[2]) * dT) // np.int32(128)
        OFF = np.int64(C[1]) * np.int32(131072) + (np.int64(C[3]) * dT) // np.int32(64)
        P = (D1_pres * SENS // np.int32(2097152) - OFF) // np.int32(32768)
    else:
        SENS = np.int64(C[0]) * np.int64(32768) + (np.int64(C[2]) * np.int64(dT)) // np.int64(256)
        OFF = np.int64(C[1]) * np.int64(65536) + (np.int64(C[3]) * np.int64(dT)) // np.int64(128)
        P = np.int32((np.int64(D1_pres) * SENS // np.int64(2097152) - OFF) // np.int64(8192))

    TEMP = np.int64(2000) + np.int64(dT) * np.int64(C[5]) // np.int64(8388608)

    if model == MS5837_02BA:
        if (TEMP / 100) < 20:
            Ti = (11 * np.int64(dT) * np.int64(dT)) // np.int64(34359738368)
            OFFi = (31 * (TEMP - 2000) * (TEMP - 2000)) // 8
            SENSi = (63 * (TEMP - 2000) * (TEMP - 2000)) // 32
    else:
        if (TEMP / 100) < 20:
            Ti = (3 * np.int64(dT) * np.int64(dT)) // np.int64(8589934592)
            OFFi = (3 * (TEMP - 2000) * (TEMP - 2000)) // 2
            SENSi = (5 * (TEMP - 2000) * (TEMP - 2000)) // 8
            if (TEMP / 100) < -15:
                OFFi = np.int64(OFFi) + 7 * (TEMP + np.int64(1500)) * (TEMP + np.int64(1500))
                SENSi = np.int64(SENSi) + 4 * (TEMP + np.int64(1500)) * (TEMP + np.int64(1500))
        elif (TEMP / 100) >= 20:
            Ti = 2 * (np.int64(dT) * np.int64(dT)) // np.int64(137438953472)
            OFFi = (1 * (np.int64(TEMP) - 2000) * (np.int64(TEMP) - 2000)) // 16
            SENSi = 0

    OFF2 = OFF - OFFi
    SENS2 = SENS - SENSi
    TEMP = np.int32((TEMP - Ti))

    if model == MS5837_02BA:
        P = (((D1_pres * SENS2) // np.int32(2097152) - OFF2) // np.int32(32768))
    else:
        P = np.int32((((np.int64(D1_pres) * SENS2) // np.int64(2097152) - OFF2) // np.int64(8192)))

    return P, TEMP

def parse_data(serial_data):
    old_serial_data = serial_data
    
    # Find EOF index
    index_end = serial_data.find(b'\x00E\x00O\x00F')
    if index_end == -1:
        raise ValueError("EOF not found in serial data.")
    
    # Find SOF index
    index_sof = serial_data.find(b'\x00S\x00O\x00F')
    if index_sof == -1:
        raise ValueError("SOF not found in serial data.")
    
    serial_data = serial_data[index_sof+6:index_end]

    # Find start of P
    index_start = serial_data.find(b'\x00P\x00,')
    if index_start == -1:
        raise ValueError("Start of 'P' not found in serial data.")
    index_start += 4
    index_start += 4

    # Extract coefficients
    C = np.zeros(7, dtype=np.uint16)
    for i in range(7):
        C[i] = int(serial_data[index_start + i*4 - 3]) * 256 + int(serial_data[index_start + i*4 - 1])
    
    # # Exclude indices with 'pr'
    # include_indices = np.ones(len(serial_data), dtype=bool)
    # indices_pr = [m.start() for m in re.finditer(b'\x00p\x00r', serial_data)]
    # for idx in indices_pr:
    #     include_indices[idx:idx+4] = False

    # serial_data = serial_data[include_indices]
    
    # Exclude indices with 'pr'
    include_indices = np.ones(len(serial_data), dtype=bool)
    indices_pr = [m.start() for m in re.finditer(b'\x00p\x00r', serial_data)]
    for idx in indices_pr:
        include_indices[idx:idx+4] = False

    serial_data = bytes([serial_data[i] for i in range(len(serial_data)) if include_indices[i]])
    print(serial_data)
    # Find start of DD
    index_start = serial_data.find(b'\x00,\x12D\x12D')
    if index_start == -1:
        raise ValueError("Start of 'DD' not found in serial data.")
    index_start += 6

    # Load all data into raw_data
    raw_data = []
    temp_counter = 0
    i = index_start
    while i < len(serial_data):
        D1_pres = np.uint32(np.float64(serial_data[i]) * (2 ** 8))
        
        if i >= len(serial_data):
            break
        
        i += 1
        D1_pres += serial_data[i]
        
        if temp_counter < 1:
            D2_temp = np.uint32(0)
            temp_counter += 1
        else:
            if i >= len(serial_data):
                break
            
            i += 1
            D2_temp = np.uint32(serial_data[i] * (2 ** 8))
            
            if i >= len(serial_data):
                break
            
            i += 1
            D2_temp += serial_data[i]
            temp_counter = 0
        
        raw_data.append([D1_pres, D2_temp])
        
        i += 1
    
    raw_data = np.array(raw_data, dtype=np.uint32)

    # Extrapolate temp values
    if len(raw_data) > 1:
        raw_data[0, 1] = raw_data[1, 1]
        if raw_data[-1, 1] == 0:
            raw_data[-1, 1] = raw_data[-2, 1]
        for i in range(2, len(raw_data) - 1):
            if raw_data[i, 1] == 0:
                raw_data[i, 1] = round((raw_data[i - 1, 1] + raw_data[i + 1, 1]) / 2)

    # Convert all pairs
    processed_data = []
    for d1_pres, d2_temp in raw_data:
        P, TEMP = calculate_pressure_temperature_original(d1_pres, d2_temp, C[1:])
        processed_data.append([P, TEMP])
    
    processed_data = np.array(processed_data, dtype=np.float64)

    # Create time array and combine with processed data
    time = np.arange(0.2, 0.2 * (len(processed_data) + 1), 0.2) - 0.2
    time = np.round(time, decimals=2)
    processed_data = np.column_stack((time, processed_data))

    # Save to file
    filename = f"Data_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    pd.DataFrame(processed_data).to_csv(filename, header=False, index=False)
    
    # Update text file list
    new_string = old_serial_data[:index_sof].decode() + f"Wrote {len(processed_data)} to file."

    return processed_data,filename

def get_processed_data(file_path):
    hex_filename = f"Hex_{file_path}"
    hex_values = hex_to_binary_file(file_path)

    print(hex_values)
    # Specify the filename
    filename = hex_filename
    # filename = 'data_2024-06-10_14-18-50.txt'

    # Open the file in binary mode
    with open(filename, 'rb') as file:
        # Read all data from the file
        data = file.read()

    # Print the raw binary data (optional, for debugging purposes)
    print(data)

    # Optionally, process the binary data here
    # For example, if you know the data is a sequence of integers, you can convert it to a list of integers
    # Assuming each integer is 1 byte in size (e.g., values 0-255)
    byte_values = list(data)

    # Print the list of integer values (optional, for debugging purposes)
    print(byte_values)
    processed_data,filename = parse_data(data)
    return processed_data
    
def produce_plots(processed_data):
    # Extract columns
    time = processed_data[:, 0]
    data_col2 = processed_data[:, 1]
    data_col3 = processed_data[:, 2]

    # Convert second column to centimeters
    data_col2_cm = (data_col2 - np.min(data_col2))/ 10

    # Convert third column to temperature
    data_col3_temp = data_col3 / 100

    # Create a DataFrame for easier plotting
    df = pd.DataFrame({
        'Time': time,
        'Data Column 2 (cm)': data_col2_cm,
        'Data Column 3 (°C)': data_col3_temp
    })

    # Plot the second column (centimeters)
    fig1 = px.line(df, x='Time', y='Data Column 2 (cm)', title='Data Column 2 in Centimeters')
    # fig1.show()

    # Plot the third column (temperature)
    fig2 = px.line(df, x='Time', y='Data Column 3 (°C)', title='Data Column 3 in Temperature (°C)')
    # fig2.show()
    return fig1,fig2

def list_text_files():
    # Get the current directory
    current_directory = os.getcwd()
    
    # List all files in the current directory
    files = os.listdir(current_directory)
    
    # Filter text files that do not start with "Data_" or "Hex_"
    filtered_files = [
        f for f in files 
        if f.endswith('.txt') and not (f.startswith('Data_') or f.startswith('Hex_'))
    ]
    
    return filtered_files