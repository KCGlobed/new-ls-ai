import time

class ObservabilityTracker:
    """
    A simple context manager/tracker for capturing latency and metrics
    across the RAG pipeline stages.
    """
    def __init__(self):
        self.metrics = {}
        self.start_time = None
        
    def start(self):
        self.start_time = time.time()
        self.metrics = {}
        return self
        
    def log(self, key: str, value: any):
        """Log a specific metric."""
        self.metrics[key] = value
        
    def log_latency(self, stage_name: str, start: float, end: float):
        """Log latency for a specific pipeline stage in milliseconds."""
        self.metrics[f"{stage_name}_ms"] = round((end - start) * 1000, 2)
        
    def finish(self) -> dict:
        if self.start_time:
            self.metrics["total_pipeline_ms"] = round((time.time() - self.start_time) * 1000, 2)
        return self.metrics
