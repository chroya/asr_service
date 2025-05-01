import os
import time
import logging
import numpy as np
import torch
from concurrent.futures import ProcessPoolExecutor
import matplotlib.pyplot as plt
from datetime import datetime

from app.core.config import settings
from app.utils.gpu_monitor import get_gpu_memory_info, get_celery_concurrency

logger = logging.getLogger(__name__)
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issues

def simulate_gpu_workload(task_id, duration=10, memory_usage=1000):
    """
    Simulate GPU memory and computation workload with real GPU computations
    
    Args:
        task_id: Task ID
        duration: Approximate target duration in seconds
        memory_usage: GPU memory allocation in MB
    
    Returns:
        dict: Execution result information
    """
    start_time = time.time()
    logger.info(f"Task {task_id} started at {datetime.now().isoformat()}")
    
    # Record initial GPU status
    total_mem, free_mem = get_gpu_memory_info()
    logger.info(f"Task {task_id} initial GPU memory: Total={total_mem}MB, Free={free_mem}MB")
    
    # Try to allocate specified GPU memory and perform computation
    try:
        # Create a large tensor to use specified memory
        tensor_size = (memory_usage * 256 * 1024) // 4  # Convert MB to number of float32 elements
        x = torch.rand(tensor_size, dtype=torch.float).cuda()
        
        # Prepare matrices for intensive computation
        # Create matrices large enough for computation but small enough to be manageable
        matrix_size = 2000  # Size of square matrix
        A = torch.rand((matrix_size, matrix_size), dtype=torch.float).cuda()
        B = torch.rand((matrix_size, matrix_size), dtype=torch.float).cuda()
        
        # Keep track of the elapsed time
        elapsed = 0
        iterations = 0
        target_end_time = start_time + duration
        
        # Perform intensive computation until the duration is reached
        while time.time() < target_end_time:
            iterations += 1
            iter_start = time.time()
            
            # Matrix multiplication (very GPU intensive)
            C = torch.matmul(A, B)
            
            # More operations to ensure GPU utilization
            D = torch.nn.functional.relu(C)
            E = torch.sin(D) + torch.cos(D)
            F = torch.mean(E, dim=0)
            G = torch.std(F)
            
            # Ensure computation result is not optimized away
            result = float(G)
            
            # Force synchronization to accurately measure time
            torch.cuda.synchronize()
            
            iter_time = time.time() - iter_start
            elapsed += iter_time
            
            # Log progress every few iterations
            if iterations % 5 == 0 or time.time() >= target_end_time:
                current_total, current_free = get_gpu_memory_info()
                percent_complete = min(100, (time.time() - start_time) / duration * 100)
                logger.info(f"Task {task_id} progress: {percent_complete:.1f}%, "
                           f"iterations: {iterations}, "
                           f"GPU memory: Total={current_total}MB, Free={current_free}MB")
        
        # Record some statistics about the computation
        computation_stats = {
            "iterations": iterations,
            "avg_iteration_time": elapsed / iterations if iterations > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Task {task_id} execution error: {str(e)}")
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e),
            "start_time": start_time,
            "end_time": time.time(),
            "duration": time.time() - start_time
        }
    finally:
        # Manually free GPU memory
        torch.cuda.empty_cache()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Record final GPU status
    total_mem, free_mem = get_gpu_memory_info()
    logger.info(f"Task {task_id} completed at {datetime.now().isoformat()}, duration: {execution_time:.2f}s")
    logger.info(f"Task {task_id} performed {iterations} computation iterations, avg time per iteration: {computation_stats['avg_iteration_time']:.4f}s")
    logger.info(f"Task {task_id} final GPU memory: Total={total_mem}MB, Free={free_mem}MB")
    
    return {
        "task_id": task_id,
        "status": "completed",
        "start_time": start_time,
        "end_time": end_time,
        "execution_time": execution_time,
        "computation_stats": computation_stats
    }


def run_concurrent_test(num_tasks=3, task_duration=20, memory_per_task=4000):
    """
    Run concurrent GPU test with multiple processes
    
    Args:
        num_tasks: Number of concurrent tasks
        task_duration: Duration of each task in seconds
        memory_per_task: Memory used by each task in MB
    
    Returns:
        list: Results of all tasks
    """
    logger.info(f"Starting GPU concurrency test: {num_tasks} tasks, each running for {task_duration}s, using {memory_per_task}MB of GPU memory")
    
    # Get GPU and Celery configuration
    total_mem, free_mem = get_gpu_memory_info()
    celery_concurrency = get_celery_concurrency()
    
    logger.info(f"GPU Memory: Total={total_mem}MB, Free={free_mem}MB")
    logger.info(f"Celery configured concurrency: {celery_concurrency}")
    
    # Check if there's enough memory
    required_memory = num_tasks * memory_per_task
    if required_memory > total_mem:
        logger.warning(f"Warning: Tasks require {required_memory}MB of memory, but GPU only has {total_mem}MB total")
    
    # Use ProcessPoolExecutor to simulate Celery's multi-process behavior
    results = []
    with ProcessPoolExecutor(max_workers=num_tasks) as executor:
        futures = [
            executor.submit(simulate_gpu_workload, f"task_{i}", task_duration, memory_per_task)
            for i in range(num_tasks)
        ]
        
        for future in futures:
            results.append(future.result())
    
    return results


def visualize_results(results, output_file="gpu_concurrency_test.png"):
    """
    Visualize test results
    
    Args:
        results: List of test results
        output_file: Output chart filename
    """
    plt.figure(figsize=(12, 6))
    
    # Sort by task start time
    results.sort(key=lambda x: x["start_time"])
    
    # Find earliest start time
    min_time = min(r["start_time"] for r in results)
    
    # Create timeline for each task
    for i, result in enumerate(results):
        start_rel = result["start_time"] - min_time
        end_rel = result["end_time"] - min_time
        
        plt.barh(i, end_rel - start_rel, left=start_rel, height=0.5, 
                 color=f"C{i}", alpha=0.8)
        
        # Add task labels
        plt.text(start_rel, i, f"{result['task_id']}", va='center', ha='right', fontsize=8)
        plt.text(end_rel, i, f"{result['execution_time']:.1f}s", va='center', ha='left', fontsize=8)
        
        # Add computation iterations if available
        if "computation_stats" in result and "iterations" in result["computation_stats"]:
            plt.text(start_rel + (end_rel - start_rel)/2, i, 
                    f"{result['computation_stats']['iterations']} iters", 
                    va='center', ha='center', fontsize=7, color='white')
    
    plt.yticks(range(len(results)), [r["task_id"] for r in results])
    plt.xlabel('Time (seconds)')
    plt.title('GPU Task Concurrent Execution Timeline')
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add performance statistics
    execution_times = [r["execution_time"] for r in results]
    avg_time = np.mean(execution_times)
    max_time = max(execution_times)
    min_time = min(execution_times)
    
    # Add computation iterations to stats if available
    iterations = []
    for r in results:
        if "computation_stats" in r and "iterations" in r["computation_stats"]:
            iterations.append(r["computation_stats"]["iterations"])
    
    if iterations:
        avg_iterations = np.mean(iterations)
        total_iterations = sum(iterations)
        stats_text = (
            f"Statistics:\n"
            f"Number of tasks: {len(results)}\n"
            f"Average execution time: {avg_time:.2f}s\n"
            f"Maximum execution time: {max_time:.2f}s\n"
            f"Minimum execution time: {min_time:.2f}s\n"
            f"Total GPU operations: {total_iterations:.0f}\n"
            f"Avg operations per task: {avg_iterations:.1f}"
        )
    else:
        stats_text = (
            f"Statistics:\n"
            f"Number of tasks: {len(results)}\n"
            f"Average execution time: {avg_time:.2f}s\n"
            f"Maximum execution time: {max_time:.2f}s\n"
            f"Minimum execution time: {min_time:.2f}s\n"
        )
    
    plt.figtext(0.7, 0.15, stats_text, fontsize=9, 
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))
    
    plt.tight_layout()
    plt.savefig(output_file)
    logger.info(f"Results chart saved to {output_file}")
    
    return output_file


def main():
    """Main test function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('gpu_concurrency_test.log')
        ]
    )
    
    # Get Celery's configured concurrency
    celery_concurrency = get_celery_concurrency()
    
    # Run concurrency test
    num_tasks = celery_concurrency  # Use same concurrency as Celery
    task_duration = 30  # Task duration 30 seconds
    memory_per_task = 5000  # Each task uses 5GB of GPU memory
    
    logger.info(f"=== GPU Concurrency Test Started ===")
    logger.info(f"Test config: {num_tasks} tasks, each running for {task_duration}s, using {memory_per_task}MB of GPU memory")
    
    results = run_concurrent_test(num_tasks, task_duration, memory_per_task)
    
    # Visualize results
    output_file = visualize_results(results)
    
    logger.info(f"=== GPU Concurrency Test Completed ===")
    logger.info(f"Results chart saved to: {output_file}")
    
    # Determine if execution was truly parallel
    execution_times = [r["execution_time"] for r in results]
    min_start = min(r["start_time"] for r in results)
    max_end = max(r["end_time"] for r in results)
    total_span = max_end - min_start
    
    # If total span time is close to single task execution time, it's parallel
    # If total span time is close to sum of all task times, it's serial
    sum_times = sum(execution_times)
    parallel_ratio = total_span / sum_times
    
    # Also analyze computation iterations if available
    iterations_data = []
    for r in results:
        if "computation_stats" in r and "iterations" in r["computation_stats"]:
            iterations_data.append(r["computation_stats"]["iterations"])
    
    # Check for variation in iterations (high variation suggests resource contention)
    if iterations_data:
        min_iterations = min(iterations_data)
        max_iterations = max(iterations_data)
        iteration_variation = (max_iterations - min_iterations) / max_iterations if max_iterations > 0 else 0
        logger.info(f"Iteration analysis: min={min_iterations}, max={max_iterations}, variation={iteration_variation:.2f}")
        
        # If variation is high, tasks are likely competing for resources
        iteration_analysis = ""
        if iteration_variation > 0.3:
            iteration_analysis = " (High variation in computation iterations suggests resource contention)"
    else:
        iteration_analysis = ""
    
    if parallel_ratio < 0.6:  # If total time is less than 60% of total execution times, good parallelism
        conclusion = f"Tasks achieved good parallel execution on GPU{iteration_analysis}"
    elif parallel_ratio < 0.8:  # Between 60%-80%, partial parallelism
        conclusion = f"Tasks achieved partial parallel execution on GPU{iteration_analysis}"
    else:  # Greater than 80%, close to serial
        conclusion = f"Tasks executed nearly serially on GPU, poor parallelism{iteration_analysis}"
    
    logger.info(f"Test conclusion: {conclusion}")
    logger.info(f"Parallel ratio: {parallel_ratio:.2f} (closer to 0 means perfect parallelism, closer to 1 means serial)")
    
    return results, output_file, conclusion


if __name__ == "__main__":
    main() 