"""S6: the wiki RAG branch, in the `rag` database on RDS (pgvector), on a daily schedule.

- wiki_pages: the published pages from the ops wiki (resource `wiki`: labpipes/wiki.py). Store each
  page's ETag and send it next time: an unchanged page then costs a 304 and no body.
- wiki_chunks: split changed pages with labpipes.chunking.chunk_markdown (chunk size and overlap are
  decision 015) and store the chunks; use Chunk.content_hash as the id so unchanged text keeps it.
- wiki_embeddings: embed only the chunks that have no vector yet (resource `embed`: nomic-embed-text,
  768 dimensions) and store them as pgvector `vector(768)`, with an index (HNSW or IVFFlat: decision 016).
- A blocking check that every chunk has a vector, and a schedule (and a job you can run by hand with
  scripts/dagster-run.sh) for the three.
"""

from __future__ import annotations

from dagster import AssetCheckResult, AssetCheckSeverity, AssetSelection, MaterializeResult, MetadataValue, ScheduleDefinition, asset, asset_check, define_asset_job

from labpipes.chunking import chunk_markdown
from labpipes.resources import LlmEmbed, RagStore, WikiApi

MAX_TOKENS = 250       # decision 015
OVERLAP_TOKENS = 40    # decision 015


def _ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id VARCHAR(128) PRIMARY KEY,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                etag TEXT NOT NULL,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id VARCHAR(64) PRIMARY KEY,
                page_id VARCHAR(128) REFERENCES pages(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                heading TEXT NOT NULL,
                chunk_index INT NOT NULL,
                content TEXT NOT NULL,
                tokens INT NOT NULL,
                embedding vector(768)
            );
            CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx 
            ON chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
            """
        )
    conn.commit()


@asset(group_name="rag", compute_kind="python")
def wiki_pages(context, wiki: WikiApi, rag: RagStore) -> MaterializeResult:
    client = wiki.client()
    pages_ref = client.pages()
    
    with rag.connect() as conn:
        _ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT id, etag FROM pages;")
            existing_etags = dict(cur.fetchall())

            fetched = 0
            unchanged = 0
            for pref in pages_ref:
                stored_etag = existing_etags.get(pref.id)
                page = client.page(pref.id, etag=stored_etag)
                if page is None:
                    unchanged += 1
                else:
                    fetched += 1
                    cur.execute(
                        """
                        INSERT INTO pages (id, title, updated_at, etag, body)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            updated_at = EXCLUDED.updated_at,
                            etag = EXCLUDED.etag,
                            body = EXCLUDED.body;
                        """,
                        (page.id, page.title, page.updated_at, page.etag, page.body)
                    )
        conn.commit()

    context.log.info(f"wiki_pages: {fetched} fetched, {unchanged} unchanged (304)")
    return MaterializeResult(
        metadata={
            "pages_fetched": MetadataValue.int(fetched),
            "pages_unchanged": MetadataValue.int(unchanged),
            "total_pages": MetadataValue.int(len(pages_ref)),
        }
    )


@asset(deps=[wiki_pages], group_name="rag", compute_kind="python")
def wiki_chunks(context, rag: RagStore) -> MaterializeResult:
    with rag.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, body FROM pages;")
            pages = cur.fetchall()

            new_chunks_count = 0
            total_chunks = 0
            for page_id, title, body in pages:
                chunks = chunk_markdown(title, body, max_tokens=MAX_TOKENS, overlap_tokens=OVERLAP_TOKENS)
                total_chunks += len(chunks)
                for ch in chunks:
                    ch_id = ch.content_hash(page_id)
                    cur.execute(
                        """
                        INSERT INTO chunks (id, page_id, title, heading, chunk_index, content, tokens)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        (ch_id, page_id, title, ch.heading, ch.index, ch.text, ch.tokens)
                    )
                    if cur.rowcount > 0:
                        new_chunks_count += 1
        conn.commit()

    context.log.info(f"wiki_chunks: {new_chunks_count} new chunks, {total_chunks} total chunks")
    return MaterializeResult(
        metadata={
            "new_chunks": MetadataValue.int(new_chunks_count),
            "total_chunks": MetadataValue.int(total_chunks),
        }
    )


@asset(deps=[wiki_chunks], group_name="rag", compute_kind="python")
def wiki_embeddings(context, embed: LlmEmbed, rag: RagStore) -> MaterializeResult:
    with rag.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content FROM chunks WHERE embedding IS NULL;")
            unembedded = cur.fetchall()

            embedded_count = 0
            if unembedded:
                ids = [row[0] for row in unembedded]
                texts = [row[1] for row in unembedded]
                context.log.info(f"Embedding {len(texts)} chunks...")
                vectors = embed.embed_documents(texts)
                
                for cid, vec in zip(ids, vectors, strict=True):
                    cur.execute("UPDATE chunks SET embedding = %s WHERE id = %s;", (vec, cid))
                embedded_count = len(vectors)
        conn.commit()

    context.log.info(f"wiki_embeddings: {embedded_count} chunks embedded")
    return MaterializeResult(
        metadata={
            "embedded_count": MetadataValue.int(embedded_count),
        }
    )


@asset_check(asset=wiki_embeddings, blocking=True, description="Every chunk in rag.chunks has an embedding vector.")
def embeddings_complete(rag: RagStore) -> AssetCheckResult:
    with rag.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM chunks WHERE embedding IS NULL;")
            missing = cur.fetchone()[0]
    return AssetCheckResult(
        passed=missing == 0,
        severity=AssetCheckSeverity.ERROR,
        description=f"{missing} chunks missing embeddings",
        metadata={"missing_embeddings": MetadataValue.int(missing)},
    )


ingest_wiki = define_asset_job(
    name="ingest_wiki",
    selection=AssetSelection.assets(wiki_pages, wiki_chunks, wiki_embeddings),
)

daily_wiki_schedule = ScheduleDefinition(
    job=ingest_wiki,
    cron_schedule="0 4 * * *",  # Run daily at 04:00 UTC
)
