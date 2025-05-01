#!/usr/bin/env python
import os
import sys
import argparse

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.tests.test_gpu_concurrency import main, run_concurrent_test, visualize_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPU Concurrency Testing Tool")
    parser.add_argument("--tasks", type=int, default=0, 
                        help="Number of concurrent tasks, defaults to Celery's configured concurrency")
    parser.add_argument("--duration", type=int, default=30, 
                        help="Duration of each task in seconds")
    parser.add_argument("--memory", type=int, default=5000, 
                        help="Memory used by each task in MB")
    parser.add_argument("--output", type=str, default="gpu_concurrency_test.png", 
                        help="Output chart filename")
    
    args = parser.parse_args()
    
    if args.tasks > 0:
        # Run test with specified parameters
        print(f"Running GPU concurrency test with custom parameters...")
        results = run_concurrent_test(args.tasks, args.duration, args.memory)
        visualize_results(results, args.output)
    else:
        # Run full test with default parameters
        print(f"Running complete GPU concurrency test...")
        main()
    
    print("Test completed. Please check the log file for more information: gpu_concurrency_test.log") 