#!/usr/bin/env python3
"""
Example script to search for founders on LinkedIn and extract their profile information.
"""

from linkedin_scraper import LinkedInScraper


def main():
    # Replace with your LinkedIn credentials
    email = input("Enter your LinkedIn email: ")
    password = input("Enter your LinkedIn password: ")

    # Initialize the scraper
    scraper = LinkedInScraper(email, password)

    # Define search parameters
    search_term = "founder startup"  # Search for founders of startups
    num_pages = 2  # Limit to 2 pages for this example

    print(f"\nSearching for '{search_term}' on LinkedIn...")
    print(f"Will scrape up to {num_pages} pages of search results.")
    print("This may take a few minutes. Please wait...\n")

    try:
        # Run the complete scraping process
        scraper.setup_driver()
        if scraper.login():
            scraper.search_people(search_term, num_pages)
            scraper.save_to_csv("founders_data.csv")
        scraper.close()

        print("\nScraping completed successfully!")
        print("Check 'founders_data.csv' for the extracted profile information.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        scraper.close()


if __name__ == "__main__":
    main()
