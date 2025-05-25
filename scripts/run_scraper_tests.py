#!/usr/bin/env python3
"""
Script to run automated scraper resilience tests.
This script can be run manually or scheduled as a cron job.
"""

import asyncio
import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_scraper_resilience import ScraperResilienceTestSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_test_logs.txt'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_baseline_tests():
    """Run baseline scraper tests."""
    logger.info("Starting baseline scraper tests...")
    
    test_suite = ScraperResilienceTestSuite()
    
    try:
        # Run baseline tests
        results = await test_suite.run_baseline_test()
        
        # Generate report
        report = test_suite.generate_report({"current_results": results})
        print("\n" + "="*60)
        print("BASELINE TEST RESULTS")
        print("="*60)
        print(report)
        
        # Save results
        filename = test_suite.save_results({"current_results": results})
        logger.info(f"Baseline test results saved to: {filename}")
        
        return results
        
    except Exception as e:
        logger.error(f"Baseline tests failed: {e}", exc_info=True)
        return None

async def run_regression_tests():
    """Run regression tests against existing baseline."""
    logger.info("Starting regression tests...")
    
    test_suite = ScraperResilienceTestSuite()
    
    try:
        # First establish baseline if not exists
        if not test_suite.baseline_data:
            logger.info("No baseline data found. Running baseline test first...")
            await test_suite.run_baseline_test()
        
        # Run regression tests
        results = await test_suite.run_regression_test()
        
        # Generate report
        report = test_suite.generate_report(results)
        print("\n" + "="*60)
        print("REGRESSION TEST RESULTS")
        print("="*60)
        print(report)
        
        # Save results
        filename = test_suite.save_results(results)
        logger.info(f"Regression test results saved to: {filename}")
        
        # Check if there are significant issues
        analysis = results.get("regression_analysis", {})
        overall_status = analysis.get("overall_status", "unknown")
        
        if overall_status == "performance_degradation":
            logger.warning("ALERT: Performance degradation detected!")
            return False
        elif overall_status == "changes_detected":
            logger.warning("ALERT: Website changes detected!")
            return False
        else:
            logger.info("All tests passed successfully.")
            return True
            
    except Exception as e:
        logger.error(f"Regression tests failed: {e}", exc_info=True)
        return False

async def run_continuous_monitoring():
    """Run continuous monitoring tests."""
    logger.info("Starting continuous monitoring...")
    
    test_suite = ScraperResilienceTestSuite()
    
    # Run tests every hour for 24 hours (or until interrupted)
    test_count = 0
    max_tests = 24
    
    try:
        while test_count < max_tests:
            logger.info(f"Running monitoring test {test_count + 1}/{max_tests}")
            
            # Run a quick baseline test
            results = await test_suite.run_baseline_test()
            
            if results:
                # Check for any immediate issues
                url_tests = results.get("url_tests", {})
                failed_urls = [url for url, result in url_tests.items() 
                             if result.get("status") != "success"]
                
                if failed_urls:
                    logger.warning(f"Failed URLs detected: {failed_urls}")
                    
                    # Save alert results
                    alert_filename = f"scraper_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    test_suite.save_results({"alert_results": results}, alert_filename)
                    logger.warning(f"Alert results saved to: {alert_filename}")
                
                logger.info(f"Monitoring test {test_count + 1} completed successfully")
            else:
                logger.error(f"Monitoring test {test_count + 1} failed")
            
            test_count += 1
            
            # Wait 1 hour before next test (or 5 minutes for testing)
            wait_time = 300 if os.getenv("TESTING_MODE") else 3600
            logger.info(f"Waiting {wait_time} seconds before next test...")
            await asyncio.sleep(wait_time)
            
    except KeyboardInterrupt:
        logger.info("Continuous monitoring interrupted by user")
    except Exception as e:
        logger.error(f"Continuous monitoring failed: {e}", exc_info=True)

def main():
    """Main function to handle command line arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run scraper resilience tests")
    parser.add_argument(
        "mode",
        choices=["baseline", "regression", "continuous"],
        help="Test mode to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--testing-mode",
        action="store_true",
        help="Enable testing mode (shorter wait times)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.testing_mode:
        os.environ["TESTING_MODE"] = "1"
    
    logger.info(f"Starting scraper tests in {args.mode} mode")
    
    try:
        if args.mode == "baseline":
            result = asyncio.run(run_baseline_tests())
            sys.exit(0 if result else 1)
            
        elif args.mode == "regression":
            result = asyncio.run(run_regression_tests())
            sys.exit(0 if result else 1)
            
        elif args.mode == "continuous":
            asyncio.run(run_continuous_monitoring())
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 