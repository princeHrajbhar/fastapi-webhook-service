"""Prometheus metrics collection."""
from collections import defaultdict
from typing import Dict, List
import threading


class MetricsCollector:
    """Thread-safe metrics collector for Prometheus exposition."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._http_requests: Dict[tuple, int] = defaultdict(int)
        self._webhook_requests: Dict[str, int] = defaultdict(int)
        self._request_latencies: List[float] = []
    
    def record_http_request(self, path: str, status: int):
        """Record HTTP request by path and status."""
        with self._lock:
            self._http_requests[(path, status)] += 1
    
    def record_webhook_request(self, result: str):
        """Record webhook request outcome."""
        with self._lock:
            self._webhook_requests[result] += 1
    
    def record_latency(self, latency_ms: float):
        """Record request latency in milliseconds."""
        with self._lock:
            self._request_latencies.append(latency_ms)
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        with self._lock:
            # HTTP requests total
            lines.append("# HELP http_requests_total Total HTTP requests by path and status")
            lines.append("# TYPE http_requests_total counter")
            for (path, status), count in sorted(self._http_requests.items()):
                lines.append(f'http_requests_total{{path="{path}",status="{status}"}} {count}')
            
            # Webhook requests total
            lines.append("# HELP webhook_requests_total Total webhook requests by result")
            lines.append("# TYPE webhook_requests_total counter")
            for result, count in sorted(self._webhook_requests.items()):
                lines.append(f'webhook_requests_total{{result="{result}"}} {count}')
            
            # Request latency
            if self._request_latencies:
                lines.append("# HELP request_latency_ms Request latency in milliseconds")
                lines.append("# TYPE request_latency_ms summary")
                
                sorted_latencies = sorted(self._request_latencies)
                count = len(sorted_latencies)
                total = sum(sorted_latencies)
                
                lines.append(f"request_latency_ms_count {count}")
                lines.append(f"request_latency_ms_sum {total}")
                
                # Quantiles
                if count > 0:
                    p50_idx = int(count * 0.5)
                    p90_idx = int(count * 0.9)
                    p99_idx = int(count * 0.99)
                    
                    lines.append(f'request_latency_ms{{quantile="0.5"}} {sorted_latencies[p50_idx]}')
                    lines.append(f'request_latency_ms{{quantile="0.9"}} {sorted_latencies[p90_idx]}')
                    lines.append(f'request_latency_ms{{quantile="0.99"}} {sorted_latencies[p99_idx]}')
        
        return "\n".join(lines) + "\n"


# Global metrics collector instance
metrics = MetricsCollector()
