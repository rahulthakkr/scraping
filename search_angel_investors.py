#!/usr/bin/env python3
"""
Script to search for Angel Investors on LinkedIn and extract their profile information.
This simplified version only visits one profile.
"""

from linkedin_scraper import LinkedInScraper


def main():
    # Replace with your LinkedIn credentials
    email = input("Enter your LinkedIn email: ")
    password = input("Enter your LinkedIn password: ")

    # Initialize the scraper
    scraper = LinkedInScraper(email, password)

    # Define search parameters
    search_term = "angel investor"  # Search for angel investors

    print(f"\nSearching for '{search_term}' on LinkedIn...")
    print("Will visit only the first profile found.")
    print("This may take a few minutes. Please wait...\n")

    try:
        # Run the simplified scraping process
        scraper.setup_driver()
        if scraper.login():
            scraper.visit_first_profile(search_term)
            scraper.save_to_csv("angel_investor_profile.csv")
        scraper.close()

        print("\nScraping completed successfully!")
        print(
            "Check 'angel_investor_profile.csv' for the extracted profile information."
        )

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        scraper.close()


if __name__ == "__main__":
    main()
