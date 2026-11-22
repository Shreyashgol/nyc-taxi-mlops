# 016: HNSW index for pgvector chunk embeddings

Stage: S6 · Date: 2026-11-22 · Author: Shreyash · Drafted by agent: yes

## Choice

Use an HNSW index (`m = 16`, `ef_construction = 64`, vector cosine distance `vector_cosine_ops`) on `rag.chunks (embedding)`.

## Rejected alternative

**IVFFlat index:** IVFFlat partitions vectors into Voronoi cells via k-means clustering. While fast to build, it requires an adequate number of centroids and vectors upfront to build meaningful clusters, and its recall degrades significantly as new documents are added unless the index is fully rebuilt.

## Why

1. **Incremental Updates:** The ops wiki updates daily with incremental page changes. HNSW supports direct insertions without quality degradation or requiring full index rebuilds.
2. **High Recall:** HNSW provides consistently higher query recall out-of-the-box compared to IVFFlat without tuning `ivfflat.probes`.
3. **Dataset Size:** With dozens to hundreds of chunks (rather than millions), HNSW's memory overhead is completely negligible on our RDS instance.

## What would show this was wrong

If the vector database scaled to tens of millions of high-dimensional embeddings where RAM constraints made HNSW graph storage unsustainable, or if index build times became an operational bottleneck during batch re-indexing.
