

If by **CoT (Chain of Thought) prompt** you mean a **master prompt for an LLM to automatically generate a complete PPG Time-Series EDA notebook**, use the following. It instructs the model what to build without requiring internal reasoning to be exposed.

---

## Master Prompt: Generate Complete PPG Time-Series EDA Notebook

```text
You are a Senior Data Scientist specializing in Time-Series Analytics, Signal Processing, and Biomedical Data Analysis.

Generate a production-ready Jupyter Notebook (.ipynb compatible) for performing comprehensive Exploratory Data Analysis (EDA) on a PPG (Photoplethysmography) time-series dataset.

Dataset Characteristics:
- CSV file input
- Contains timestamp column and PPG sensor readings
- Example columns:
    seq
    timestamp_ms
    red
    ir
    red_corrected
    ir_corrected

Requirements:

====================================================
1. DATA LOADING
====================================================

- Load CSV using pandas
- Display shape
- Display first 5 rows
- Display data types
- Generate dataset summary

====================================================
2. DATA QUALITY ANALYSIS
====================================================

Generate:
- Missing value counts
- Missing value percentages
- Duplicate row analysis
- Data type validation
- Null value strategy recommendation

Create a summary dataframe:
Column Name
Data Type
Missing Count
Missing Percentage
Suggested Imputation Strategy

====================================================
3. FEATURE ENGINEERING
====================================================

Create the following features:

Time Features:
- time_sec
- elapsed_time

Rolling Statistics:
- rolling mean
- rolling std
- rolling min
- rolling max

Signal Features:
- first derivative
- second derivative
- signal energy
- signal magnitude

Frequency Features:
- dominant frequency
- spectral power

Peak Features:
- peak count
- peak intervals
- BPM estimation

====================================================
4. NORMALIZATION
====================================================

Implement:

A. Min-Max Scaling
Create:
- red_corrected_norm
- ir_corrected_norm

B. Z-Score Standardization
Create:
- red_corrected_zscore
- ir_corrected_zscore

Visualize:
- Original vs Normalized
- Original vs Standardized

====================================================
5. DESCRIPTIVE STATISTICS
====================================================

Generate:
- mean
- median
- std
- variance
- skewness
- kurtosis
- min
- max

Export summary table.

====================================================
6. CORRELATION ANALYSIS
====================================================

Generate:
- Correlation matrix
- Heatmap
- Feature correlation ranking

====================================================
7. TIME SERIES VISUALIZATION
====================================================

Generate plots for:

Raw Signals:
- red
- ir

Corrected Signals:
- red_corrected
- ir_corrected

Normalized Signals:
- red_corrected_norm
- ir_corrected_norm

Rolling Trend Analysis

Save all plots.

====================================================
8. SAMPLING RATE ANALYSIS
====================================================

Calculate:
- Average sampling interval
- Sampling frequency (Hz)

Display summary.

====================================================
9. FFT ANALYSIS
====================================================

Perform:
- Fast Fourier Transform

Generate:
- Frequency Spectrum Plot
- Dominant Frequency
- Estimated BPM

====================================================
10. PEAK DETECTION
====================================================

Using scipy.signal.find_peaks:

Generate:
- Peak locations
- Peak intervals
- Peak visualization
- Heart rate estimation

Display:
- Average BPM
- Number of peaks

====================================================
11. STATIONARITY ANALYSIS
====================================================

Apply Augmented Dickey-Fuller Test.

Output:
- ADF Statistic
- p-value
- Critical Values
- Interpretation

====================================================
12. ACF ANALYSIS
====================================================

Generate:
- Autocorrelation Plot
- Interpretation

====================================================
13. PACF ANALYSIS
====================================================

Generate:
- Partial Autocorrelation Plot
- Interpretation

====================================================
14. TIME SERIES DECOMPOSITION
====================================================

Perform seasonal decomposition.

Generate:
- Original
- Trend
- Seasonal
- Residual

Provide interpretation.

====================================================
15. SIGNAL QUALITY ANALYSIS
====================================================

Calculate:
- Signal Power
- Noise Power
- Signal-to-Noise Ratio (SNR)

Display results.

====================================================
16. OUTLIER DETECTION
====================================================

Apply:
- IQR Method

Generate:
- Outlier count
- Outlier plot

====================================================
17. REPORT GENERATION
====================================================

Generate final EDA summary:

Include:
- Missing data findings
- Stationarity results
- Dominant frequency
- BPM estimation
- SNR
- Outlier count
- Key observations

====================================================
18. OUTPUTS
====================================================

Save:

- Feature engineered dataset:
    ppg_feature_engineered.csv

- All plots in output/ folder

- Final EDA report

Code Requirements:
- Modular structure
- Well-commented code
- Production-ready
- Error handling
- Notebook cells organized logically
- Use pandas, numpy, scipy, matplotlib, seaborn, sklearn, statsmodels

Return only executable notebook code.
```
