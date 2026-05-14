"""
logs/audit.py
=============
Permanent audit trail for every property analysis.
Uses JSONL format (one JSON object per line).

Why JSONL:
    - Easy to append (just add a line)
    - Easy to query (read line by line)
    - Works with pandas, spark, Excel later
    - Never need to load entire file to add one record

Why this exists:
    Every enterprise client will ask:
    - "What did the system recommend on March 14?"
    - "How much has this cost us this month?"
    - "Which properties did we analyse last week?"
    Without an audit log, you cannot answer any of these.

Elite engineering principle:
    Log everything. Storage is cheap. Missing logs are expensive.
"""

import json           # for serialising records to JSON
import uuid           # for generating unique analysis IDs
import os             # for creating directories
from datetime import datetime, date  # for timestamps
from pathlib import Path             # for clean path handling


class AuditLogger:
    """
    Logs every property analysis permanently to a JSONL file.
    One line per analysis. Never overwrites. Always appends.
    """

    def __init__(self, log_dir: str = "logs"):
        """
        Initialise the audit logger.
        Creates the logs/ directory if it doesn't exist.
        
        Args:
            log_dir: Directory to store log files (default: "logs")
        """
        # Convert to Path object for clean cross-platform handling
        self.log_dir = Path(log_dir)

        # Create logs directory if it doesn't exist
        # exist_ok=True means no error if it already exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file — one record per line
        self.log_file = self.log_dir / "analysis_log.jsonl"

        # Track hits and misses for session summary
        self._total_analyses = 0   # Count of successful analyses logged
        self._total_errors = 0     # Count of errors logged

    def log_analysis(
        self,
        property_input: dict,
        metrics: dict,
        recommendation: str,
        data_sources: dict,
        model_used: str = "claude-haiku-4-5",
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        duration_seconds: float = 0.0,
    ) -> str:
        """
        Log one complete property analysis permanently.
        
        Args:
            property_input:    The property data used for analysis
            metrics:           The 35 calculated financial metrics
            recommendation:    buy/hold/avoid from Claude
            data_sources:      Dict of source labels for each data point
            model_used:        Which Claude model was used
            tokens_used:       Total tokens consumed
            cost_usd:          Estimated API cost in USD
            duration_seconds:  How long the full analysis took
            
        Returns:
            analysis_id: Unique ID for this analysis (for reference/lookup)
        """
        # Generate a unique ID for this analysis
        # UUID4 = random, globally unique, no collision risk
        analysis_id = str(uuid.uuid4())

        # Build the record — everything that could ever be needed to audit this run
        record = {
            "analysis_id": analysis_id,           # Unique reference ID
            "record_type": "ANALYSIS",            # Distinguish from ERROR records
            "timestamp": datetime.now().isoformat(),  # When this ran

            # Property details
            "property": {
                "address": property_input.get("address", "unknown"),
                "suburb": property_input.get("suburb", "unknown"),
                "city": property_input.get("city", "unknown"),
                "state": property_input.get("state", "unknown"),
                "purchase_price": property_input.get("purchase_price", 0),
            },

            # Key financial metrics — the numbers that drove the recommendation
            "key_metrics": {
                "gross_yield_pct": metrics.get("gross_yield_pct"),
                "net_yield_pct": metrics.get("net_yield_pct"),
                "monthly_cash_flow": metrics.get("monthly_cash_flow"),
                "dscr": metrics.get("dscr"),
                "projected_value_5yr": metrics.get("projected_value_5yr"),
                "capital_gain_5yr": metrics.get("capital_gain_5yr"),
                "data_quality_score": metrics.get("data_quality_score"),
            },

            # Where each data point came from — full audit trail
            "data_sources": data_sources,

            # AI decision
            "recommendation": recommendation,

            # Technical metadata — for cost tracking and debugging
            "model_used": model_used,
            "tokens_used": tokens_used,
            "cost_usd": round(cost_usd, 6),       # Round to avoid floating point noise
            "duration_seconds": round(duration_seconds, 2),

            # Version control — which benchmarks were current at time of analysis
            "benchmarks_version": str(date.today()),

            # Legal — every analysis output includes this disclaimer
            "disclaimer": (
                "Not financial advice. "
                "For educational purposes only. "
                "Consult a licensed financial adviser."
            ),
        }

        # Append to log file — one JSON object per line
        # "a" mode = append, never overwrite
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")  # Write record + newline

        # Track session count
        self._total_analyses += 1

        # Return the ID so the caller can reference this analysis
        return analysis_id

    def log_error(
        self,
        error_type: str,
        error_msg: str,
        property_input: dict,
    ) -> None:
        """
        Log an error that occurred during analysis.
        Errors are logged to the same file but with record_type="ERROR".
        
        Args:
            error_type:     Category of error (e.g. "VALIDATION_ERROR")
            error_msg:      Human-readable error description
            property_input: The input that caused the error
        """
        record = {
            "record_type": "ERROR",                    # Distinguishes from analysis records
            "timestamp": datetime.now().isoformat(),   # When the error occurred
            "error_type": error_type,                  # Category for filtering
            "error_msg": error_msg,                    # What went wrong
            "property": {
                "address": property_input.get("address", "unknown"),
                "suburb": property_input.get("suburb", "unknown"),
            },
        }

        # Append error to same log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # Track error count
        self._total_errors += 1

    def check_benchmarks_freshness(self) -> dict:
        """
        Check how old the hardcoded benchmarks are.
        Warns if benchmarks haven't been updated in over 35 days.
        
        Returns:
            dict with age_days, last_updated, is_stale, warning
        """
        try:
            # Import benchmarks to get their last_updated date
            # Import here (not at top) to avoid circular import issues
            from data.benchmarks import CITY_BENCHMARKS

            # Get last_updated from any city — they all share the same update date
            first_city = next(iter(CITY_BENCHMARKS))
            last_updated_str = CITY_BENCHMARKS[first_city]["last_updated"]
            last_updated = date.fromisoformat(last_updated_str)

            # Calculate how many days since last update
            age_days = (date.today() - last_updated).days

            # Benchmarks older than 35 days should be refreshed
            # Monthly update cadence = benchmarks can be up to 31 days old
            is_stale = age_days > 35

            warning = None
            if is_stale:
                warning = (
                    f"Benchmarks are {age_days} days old "
                    f"(last updated: {last_updated_str}). "
                    f"Update recommended — open data/benchmarks.py"
                )

            return {
                "age_days": age_days,
                "last_updated": last_updated_str,
                "is_stale": is_stale,
                "warning": warning,
            }

        except Exception as e:
            # If we can't check freshness, return a safe default
            return {
                "age_days": -1,
                "last_updated": "unknown",
                "is_stale": False,
                "warning": f"Could not check benchmark freshness: {e}",
            }

    def get_summary(self, last_n_days: int = 30) -> dict:
        """
        Summarise analyses from the last N days.
        Useful for reporting: "What did the system do last month?"
        
        Args:
            last_n_days: How many days back to look (default: 30)
            
        Returns:
            Summary dict with counts, costs, recommendations breakdown
        """
        # Return empty summary if log file doesn't exist yet
        if not self.log_file.exists():
            return {
                "total_analyses": 0,
                "recommendations": {"buy": 0, "hold": 0, "avoid": 0},
                "avg_data_quality": 0.0,
                "total_cost_usd": 0.0,
                "avg_cost_usd": 0.0,
                "errors": 0,
                "period_days": last_n_days,
            }

        # Calculate cutoff date — only include records after this
        cutoff = datetime.now().timestamp() - (last_n_days * 86400)  # 86400 = seconds per day

        # Read and parse the log file
        analyses = []   # Will hold parsed analysis records
        errors = 0      # Count errors separately

        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                try:
                    record = json.loads(line)  # Parse JSON from line

                    # Check if within date range
                    ts = datetime.fromisoformat(record["timestamp"]).timestamp()
                    if ts < cutoff:
                        continue  # Skip records older than cutoff

                    # Count errors
                    if record.get("record_type") == "ERROR":
                        errors += 1
                        continue

                    # Collect analysis records
                    if record.get("record_type") == "ANALYSIS":
                        analyses.append(record)

                except (json.JSONDecodeError, KeyError):
                    continue  # Skip malformed lines gracefully

        # Build recommendation counts
        rec_counts = {"buy": 0, "hold": 0, "avoid": 0}
        total_quality = 0.0
        total_cost = 0.0

        for a in analyses:
            # Count recommendation types
            rec = a.get("recommendation", "").lower()
            if rec in rec_counts:
                rec_counts[rec] += 1

            # Sum quality scores
            quality = a.get("key_metrics", {}).get("data_quality_score", 0)
            if quality:
                total_quality += quality

            # Sum costs
            total_cost += a.get("cost_usd", 0)

        n = len(analyses)  # Total analysis count

        return {
            "total_analyses": n,
            "recommendations": rec_counts,
            "avg_data_quality": round(total_quality / n, 2) if n > 0 else 0.0,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_usd": round(total_cost / n, 4) if n > 0 else 0.0,
            "errors": errors,
            "period_days": last_n_days,
        }


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n AUDIT LOGGER — Standalone Test\n")

    # Create logger — will make logs/ directory automatically
    logger = AuditLogger(log_dir="logs")

    # Test logging an analysis
    test_id = logger.log_analysis(
        property_input={
            "address": "14 Kangaroo Point Rd",
            "suburb": "Kangaroo Point",
            "city": "Brisbane",
            "state": "QLD",
            "purchase_price": 950000,
        },
        metrics={
            "gross_yield_pct": 4.11,
            "net_yield_pct": 2.85,
            "monthly_cash_flow": -590,
            "dscr": 0.71,
            "projected_value_5yr": 1674000,
            "capital_gain_5yr": 724000,
            "data_quality_score": 0.75,
        },
        recommendation="buy",
        data_sources={
            "rent_source": "USER_PROVIDED",
            "growth_source": "OFFICIAL: ABS RPPI",
            "vacancy_source": "BENCHMARK: SQM May 2026",
        },
        model_used="claude-haiku-4-5",
        tokens_used=487,
        cost_usd=0.0008,
        duration_seconds=4.2,
    )
    print(f"Logged analysis: {test_id}")

    # Test logging an error
    logger.log_error(
        error_type="VALIDATION_ERROR",
        error_msg="purchase_price must be positive",
        property_input={"address": "test", "suburb": "Brisbane"},
    )
    print("Logged error record")

    # Test summary
    summary = logger.get_summary(last_n_days=30)
    print(f"\nSummary (last 30 days):")
    print(f"  Total analyses: {summary['total_analyses']}")
    print(f"  Recommendations: {summary['recommendations']}")
    print(f"  Total cost: ${summary['total_cost_usd']:.4f}")

    # Test freshness check
    freshness = logger.check_benchmarks_freshness()
    print(f"\nBenchmarks age: {freshness['age_days']} days")
    if freshness["warning"]:
        print(f"  WARNING: {freshness['warning']}")
    else:
        print("  Benchmarks are current")

    print(f"\nLog file: {logger.log_file}")
