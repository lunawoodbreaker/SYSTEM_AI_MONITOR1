import cProfile
import pstats
import io
import time
import psutil
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import line_profiler
import memory_profiler
import tracemalloc

@dataclass
class PerformanceMetrics:
    execution_time: float
    memory_usage: float
    cpu_usage: float
    function_calls: Dict[str, int]
    hot_spots: List[Dict[str, Any]]
    memory_leaks: List[Dict[str, Any]]

class PerformanceProfiler:
    """Analyzes code performance and provides optimization suggestions."""
    
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.line_profiler = line_profiler.LineProfiler()
        tracemalloc.start()
    
    def profile_function(self, func, *args, **kwargs) -> PerformanceMetrics:
        """Profile a single function's performance."""
        # CPU Profiling
        self.profiler.enable()
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        self.profiler.disable()
        
        # Get profiling stats
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats()
        
        # Line profiling
        self.line_profiler.add_function(func)
        self.line_profiler.enable()
        func(*args, **kwargs)
        self.line_profiler.disable()
        
        # Memory profiling
        memory_stats = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Analyze hot spots
        hot_spots = self._analyze_hot_spots(ps)
        
        # Check for memory leaks
        memory_leaks = self._check_memory_leaks(start_memory, end_memory, memory_stats)
        
        return PerformanceMetrics(
            execution_time=end_time - start_time,
            memory_usage=end_memory - start_memory,
            cpu_usage=psutil.cpu_percent(),
            function_calls=self._get_function_calls(ps),
            hot_spots=hot_spots,
            memory_leaks=memory_leaks
        )
    
    def profile_file(self, file_path: str) -> Dict[str, Any]:
        """Profile an entire Python file."""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Create a temporary module to run the code
            namespace = {}
            self.profiler.enable()
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            exec(code, namespace)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            self.profiler.disable()
            
            # Get profiling stats
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
            ps.print_stats()
            
            # Memory profiling
            memory_stats = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            return {
                "execution_time": end_time - start_time,
                "memory_usage": end_memory - start_memory,
                "cpu_usage": psutil.cpu_percent(),
                "hot_spots": self._analyze_hot_spots(ps),
                "memory_leaks": self._check_memory_leaks(start_memory, end_memory, memory_stats),
                "function_calls": self._get_function_calls(ps)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_hot_spots(self, stats: pstats.Stats) -> List[Dict[str, Any]]:
        """Analyze code hot spots from profiling data."""
        hot_spots = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            if ct > 0.1:  # Only consider functions taking more than 0.1 seconds
                hot_spots.append({
                    "function": f"{func[0]}:{func[1]}:{func[2]}",
                    "total_time": ct,
                    "calls": nc,
                    "time_per_call": ct / nc if nc > 0 else 0
                })
        return sorted(hot_spots, key=lambda x: x["total_time"], reverse=True)
    
    def _check_memory_leaks(self, start_memory: int, end_memory: int, 
                           memory_stats: tuple) -> List[Dict[str, Any]]:
        """Check for potential memory leaks."""
        leaks = []
        if end_memory > start_memory * 1.5:  # 50% increase in memory usage
            leaks.append({
                "type": "memory_growth",
                "start_memory": start_memory,
                "end_memory": end_memory,
                "growth": end_memory - start_memory
            })
        
        if memory_stats[1] > memory_stats[0] * 2:  # Peak memory is twice the current
            leaks.append({
                "type": "memory_peak",
                "current": memory_stats[0],
                "peak": memory_stats[1]
            })
        
        return leaks
    
    def _get_function_calls(self, stats: pstats.Stats) -> Dict[str, int]:
        """Get function call counts from profiling data."""
        calls = {}
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            calls[f"{func[0]}:{func[1]}:{func[2]}"] = nc
        return calls
    
    def get_optimization_suggestions(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate optimization suggestions based on performance metrics."""
        suggestions = []
        
        # Check execution time
        if metrics.execution_time > 1.0:  # More than 1 second
            suggestions.append("Consider optimizing slow functions identified in hot spots")
        
        # Check memory usage
        if metrics.memory_usage > 100 * 1024 * 1024:  # More than 100MB
            suggestions.append("High memory usage detected. Consider implementing memory optimization techniques")
        
        # Check for memory leaks
        if metrics.memory_leaks:
            suggestions.append("Potential memory leaks detected. Review resource cleanup in your code")
        
        # Check CPU usage
        if metrics.cpu_usage > 80:  # More than 80% CPU usage
            suggestions.append("High CPU usage detected. Consider implementing parallel processing or optimizing CPU-intensive operations")
        
        # Analyze hot spots
        for spot in metrics.hot_spots:
            if spot["time_per_call"] > 0.1:  # More than 0.1 seconds per call
                suggestions.append(f"Function {spot['function']} is taking {spot['time_per_call']:.2f} seconds per call. Consider optimizing this function")
        
        return suggestions 