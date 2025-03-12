#!/usr/bin/env python3
"""
Script to search for Angel Investors on LinkedIn and extract their profile information.
This version can visit multiple profiles across multiple pages of search results.
It also enriches profile data with information from RocketReach.
"""

import os

from linkedin_scraper import LinkedInScraper


def main():
    # Replace with your LinkedIn credentials
    email = os.getenv("linkedin_email")
    password = os.getenv("linkedin_password")
    rr_api_key = os.getenv("rr_api_key")

    if email is None:
        email = input("Enter your LinkedIn email: ")
    if password is None:
        password = input("Enter your LinkedIn password: ")
    if rr_api_key is None:
        rr_api_key = input("Enter your RocketReach API key (press Enter to skip): ")

    if not rr_api_key:
        print(
            "No RocketReach API key provided. Profiles will not be enriched with additional data."
        )
        rr_api_key = None

    # Get user input for number of profiles and pages
    try:
        num_profiles = int(
            input("Enter the number of profiles to visit (default: 5): ") or "5"
        )
        max_pages = int(
            input("Enter the maximum number of pages to search (default: 3): ") or "3"
        )
    except ValueError:
        print("Invalid input. Using default values.")
        num_profiles = 5
        max_pages = 3

    # Initialize the scraper with RocketReach API key
    scraper = LinkedInScraper(email, password, rr_api_key=rr_api_key)

    # Define search parameters
    search_term = (
        input("Enter search term (default: 'angel investor'): ") or "angel investor"
    )

    print(f"\nSearching for '{search_term}' on LinkedIn...")
    print(
        f"Will visit up to {num_profiles} profiles across up to {max_pages} pages of search results."
    )
    if rr_api_key:
        print("Profiles will be enriched with RocketReach data.")
    print("This may take a few minutes. Please wait...\n")

    try:
        # Run the scraping process with pagination
        scraper.setup_driver()
        if scraper.login():
            # Use the enhanced visit_profiles method with pagination
            scraper.visit_profiles(
                search_term, num_profiles=num_profiles, max_pages=max_pages
            )
        scraper.close()

        print("\nScraping completed successfully!")
        print(
            f"Check 'linkedin_profiles_{search_term.replace(' ', '_')}.csv' for the extracted profile information."
        )

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        scraper.close()


if __name__ == "__main__":
    main()
