import zipfile
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# A function to create the plot for each file
def create_plot(df, filename):
    # Convert 'TIME' from milliseconds to seconds
    df['TIME_S'] = df['TIME'] / 1000

    # Convert bytes to kilobytes and apply log transformation with base 10
    df['BYTES_KB'] = df['BYTES'] / 1024
    df['BYTES_KB_LOG10'] = np.log10(df['BYTES_KB'])

    # Create a color map for different resolutions
    resolution_colors = {resolution: color for resolution, color in zip(df['RESOLUTION'].unique(), plt.cm.get_cmap('tab10').colors)}

    fig, ax = plt.subplots(figsize=(15, 10))

    # For each segment in the data
    for index, row in df.iterrows():
        # Create a rectangle with left edge at TIME_S, bottom at 0, width as DURATION, and height as BYTES_KB_LOG10
        rectangle = plt.Rectangle((row['TIME_S'], 0), row['DURATION'], row['BYTES_KB_LOG10'], 
                                  fc=resolution_colors[row['RESOLUTION']], alpha=0.3, 
                                  edgecolor='black', linewidth=1.0)  # Add outline
        ax.add_patch(rectangle)

    # Mark where a 'REBUF' event has occurred
    for time in df[df['REBUF'] > 0]['TIME_S']:
        ax.axvline(x=time, color='red', linestyle='--')

    # Set the title and labels
    ax.set_title(f'Time vs Bytes ($10^n$ KB) for Each Segment with Rebuffering Events - {filename}')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Bytes ($10^n$ KB)')

    # Limit the x-axis to the first 50 seconds
    ax.set_xlim(0, 50)

    # Increase the maximum value of the y-axis
    ax.set_ylim(0, df['BYTES_KB_LOG10'].max() * 1.5)

    # Create a custom legend
    custom_lines = [plt.Line2D([0], [0], color=color, lw=4) for color in resolution_colors.values()]
    ax.legend(custom_lines, resolution_colors.keys(), title='Resolutions')

    plt.show()
if __name__ == '__main__':
    # Extract the zip file again
    with zipfile.ZipFile("/mnt/data/trace_0.txt.zip", 'r') as zip_ref:
        zip_ref.extractall("/mnt/data/")

    # Load all csv files again
    csv_files = {
        'trace_0.txt.csv': pd.read_csv('/mnt/data/trace_0.txt.csv'),
        'trace_1.txt.csv': pd.read_csv('/mnt/data/trace_1.txt.csv'),
        'trace_2.txt.csv': pd.read_csv('/mnt/data/trace_2.txt.csv'),
        'trace_3.txt.csv': pd.read_csv('/mnt/data/trace_3.txt.csv'),
        'trace_4.txt.csv': pd.read_csv('/mnt/data/trace_4.txt.csv')
    }

    # Create the plot for each file
    for filename, df in csv_files.items():
        create_plot(df, filename)
