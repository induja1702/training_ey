import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.signal import find_peaks
from scipy.fft import fft, fftfreq

from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import seasonal_decompose

from sklearn.preprocessing import StandardScaler

import warnings
warnings.filterwarnings("ignore")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 2. Load dataset

FILE_PATH = "sakshi_ppg_20260611T074737_len148s.csv"

df = pd.read_csv(FILE_PATH)

print(df.shape)
df.head()

# Dataset summary
print("="*50)
print("DATASET SUMMARY")
print("="*50)

print("Rows:", df.shape[0])
print("Columns:", df.shape[1])

print("\nColumn Names")
print(df.columns.tolist())

print("\nData Types")
print(df.dtypes)

#  Missing value

missing_df = pd.DataFrame({
    "Column": df.columns,
    "Missing_Count": df.isnull().sum(),
    "Missing_%": round(df.isnull().mean()*100,2)
})

print(missing_df)

# Missing value startegy

for col in df.columns:

    pct = df[col].isnull().mean()*100

    if pct == 0:
        strategy = "No action needed"

    elif pct < 5:
        strategy = "Forward Fill"

    elif pct < 20:
        strategy = "Linear Interpolation"

    else:
        strategy = "Drop segment"

    print(col, "->", strategy)

# 6. Feature Engineering
# Time Features
df["time_sec"] = (
    df["timestamp_ms"] - df["timestamp_ms"].min()
)/1000
# Rolling Statistics
window = 50

df["red_roll_mean"] = (
    df["red_corrected"]
    .rolling(window)
    .mean()
)

df["red_roll_std"] = (
    df["red_corrected"]
    .rolling(window)
    .std()
)

df["ir_roll_mean"] = (
    df["ir_corrected"]
    .rolling(window)
    .mean()
)

df["ir_roll_std"] = (
    df["ir_corrected"]
    .rolling(window)
    .std()
)
# First Derivative
df["red_diff"] = df["red_corrected"].diff()

df["ir_diff"] = df["ir_corrected"].diff()
# Second Derivative
df["red_diff2"] = df["red_diff"].diff()

df["ir_diff2"] = df["ir_diff"].diff()
# Signal Magnitude
df["signal_energy"] = (
    df["red_corrected"]**2 +
    df["ir_corrected"]**2
)
# 7. Statistical Summary
summary = df.describe().T

summary["skewness"] = df.skew(numeric_only=True)
summary["kurtosis"] = df.kurtosis(numeric_only=True)

# summary
# 8. Correlation Matrix
plt.figure(figsize=(10,6))

sns.heatmap(
    df.corr(numeric_only=True),
    annot=True,
    cmap="coolwarm"
)

plt.title("Correlation Matrix")
plt.savefig(
    os.path.join(OUTPUT_DIR, "correlation_matrix.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 9. Raw Signal Plot
plt.figure(figsize=(15,5))

plt.plot(
    df["time_sec"],
    df["red"],
    label="RED"
)

plt.plot(
    df["time_sec"],
    df["ir"],
    label="IR"
)

plt.legend()
plt.title("Raw PPG Signals")
plt.savefig(
    os.path.join(OUTPUT_DIR, "raw_signal.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 10. Corrected Signal Plot
plt.figure(figsize=(15,5))

plt.plot(
    df["time_sec"],
    df["red_corrected"],
    label="RED Corrected"
)

plt.plot(
    df["time_sec"],
    df["ir_corrected"],
    label="IR Corrected"
)

plt.legend()
plt.title("Corrected Signals")
plt.savefig(
    os.path.join(OUTPUT_DIR, "corrected_signal.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 11. Rolling Trend
plt.figure(figsize=(15,5))

plt.plot(
    df["time_sec"],
    df["red_corrected"],
    alpha=0.5
)

plt.plot(
    df["time_sec"],
    df["red_roll_mean"],
    linewidth=3
)

plt.title("Trend using Rolling Mean")
plt.savefig(
    os.path.join(OUTPUT_DIR, "trend_mean.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 12. Sampling Frequency
time_diff = (
    df["timestamp_ms"]
    .diff()
    .dropna()
    .mean()
)

sampling_rate = 1000 / time_diff

print("Sampling Rate:", sampling_rate)
# 13. FFT Analysis
signal = df["red_corrected"].values

N = len(signal)

yf = fft(signal)

xf = fftfreq(
    N,
    d=1/sampling_rate
)

positive_idx = xf > 0

xf = xf[positive_idx]
yf = np.abs(yf[positive_idx])

plt.figure(figsize=(15,5))

plt.plot(xf, yf)

plt.xlim(0,10)

plt.title("FFT Spectrum")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude")
plt.savefig(
    os.path.join(OUTPUT_DIR, "fft_spectrum.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 14. Dominant Frequency
dominant_frequency = xf[np.argmax(yf)]

print(
    "Dominant Frequency:",
    dominant_frequency,
    "Hz"
)

bpm = dominant_frequency * 60

print("Estimated BPM:", bpm)
# 15. Peak Detection
peaks,_ = find_peaks(
    df["red_corrected"],
    distance=int(sampling_rate*0.4)
)

print("Number of Peaks:", len(peaks))
# 16. Peak Visualization
plt.figure(figsize=(15,5))

plt.plot(df["red_corrected"])

plt.scatter(
    peaks,
    df["red_corrected"].iloc[peaks],
    color="red"
)

plt.title("Detected Peaks")
plt.savefig(
    os.path.join(OUTPUT_DIR, "detected_peaks_red_corrected.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 17. BPM from Peaks
peak_times = (
    df.iloc[peaks]["time_sec"]
    .values
)

rr_intervals = np.diff(peak_times)

heart_rate = (
    60 /
    np.mean(rr_intervals)
)

print("Heart Rate:", heart_rate)
# 18. Stationarity Test (ADF)
result = adfuller(
    df["red_corrected"].dropna()
)

print("ADF Statistic:", result[0])
print("P Value:", result[1])

if result[1] < 0.05:
    print("Stationary")
else:
    print("Not Stationary")
# 19. ACF Plot
plt.figure(figsize=(12,5))

plot_acf(
    df["red_corrected"].dropna(),
    lags=50
)
plt.savefig(
    os.path.join(OUTPUT_DIR, "ADF.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 20. PACF Plot
plt.figure(figsize=(12,5))

plot_pacf(
    df["red_corrected"].dropna(),
    lags=50
)
plt.savefig(
    os.path.join(OUTPUT_DIR, "PACF.png"),
    bbox_inches="tight",
    dpi=300
)

plt.show()
# 21. Seasonal Decomposition
period = int(sampling_rate)

decomp = seasonal_decompose(
    df["red_corrected"],
    model="additive",
    period=period
)

decomp.plot()
plt.savefig(
    os.path.join(OUTPUT_DIR, "seasonal_decomposition.png"),
    bbox_inches="tight",
    dpi=300
)
plt.show()
# 22. Signal-to-Noise Ratio
signal_power = np.mean(
    df["red_corrected"]**2
)

noise = (
    df["red_corrected"] -
    df["red_roll_mean"]
)

noise_power = np.mean(
    noise.dropna()**2
)

snr = 10*np.log10(
    signal_power/noise_power
)

print("SNR:", snr,"dB")
# 23. Outlier Detection (IQR)
Q1 = df["red_corrected"].quantile(0.25)
Q3 = df["red_corrected"].quantile(0.75)

IQR = Q3-Q1

lower = Q1 - 1.5*IQR
upper = Q3 + 1.5*IQR

outliers = df[
    (df["red_corrected"] < lower) |
    (df["red_corrected"] > upper)
]

print("Outliers:", len(outliers))
# 24. Outlier Plot
plt.figure(figsize=(15,5))

plt.plot(
    df["red_corrected"],
    alpha=0.7
)

plt.scatter(
    outliers.index,
    outliers["red_corrected"],
    color="red"
)

plt.title("Outlier Detection")

plt.show()
# 25. Save EDA Dataset
df.to_csv(
    "ppg_feature_engineered.csv",
    index=False
)

print("Saved Successfully")

