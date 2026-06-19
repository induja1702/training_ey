Why latency varies (0.66s → 1.12s)

Retrieval time varies by query specificity
"Total revenue" is a broad term — the retriever scans more candidate chunks before settling on the best match → slower "Gross margin percentage" is a precise, rare phrase — fewer chunks compete, top match found quickly → faster

Number of chunks retrieved & re-ranked Your FAISS search returns top-k results. Vague queries like "cash at end of fiscal year" may pull chunks from multiple sections (balance sheet, cash flow, MD&A), requiring more re-ranking work before the LLM gets context.
Context length sent to the LLM
Longer retrieved context = more tokens the LLM has to process = slower generation "Revenue" likely pulled a large risk/summary section (Apple_10K_2023_Risk chunks tend to be dense) "Gross margin" pulled a tighter financial table row

LLM output length QueryResponse lengthLatencyTotal revenueMedium sentence + source1.12sGross marginShort percentage + source0.66sShareholders returnLongest — 3 data points0.74s* *Shareholder return was fast despite long output — the chunk was probably a single well-structured paragraph, retrieved instantly.
"Insufficient information" was the fastest of all The cash query returned almost nothing — the retriever found no strong match, returned minimal context, and the LLM output was a short failure message. Less context + shorter output = lowest possible latency.