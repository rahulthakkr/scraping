import os

from dotenv import load_dotenv

from linkedin_scraper import LinkedInScraper


def main():
    # Load environment variables
    load_dotenv()

    # Replace with your LinkedIn credentials
    email = os.getenv("linkedin_email")
    password = os.getenv("linkedin_password")
    rr_api_key = os.getenv("rr_api_key")

    if email is None:
        email = input("Enter your LinkedIn email: ")
    if password is None:
        password = input("Enter your LinkedIn password: ")

    # Ask user to choose between API and browser methods
    rr_method = input(
        "Choose RocketReach method (1 for API, 2 for Browser, default: API): "
    ).strip()
    use_api = rr_method != "2"  # Default to API unless browser option is chosen

    if use_api:
        print("Using RocketReach API for lookups")
        if rr_api_key is None:
            rr_api_key = input("Enter your RocketReach API key: ")
        if not rr_api_key:
            print(
                "No RocketReach API key provided. Will fall back to browser method if API fails."
            )
    else:
        print("Using RocketReach Browser automation for lookups")
        rr_api_key = None  # Set to None to force browser method

    # Get user input for number of profiles
    try:
        num_profiles = int(
            input("Enter the number of profiles to visit (default: 5): ") or "5"
        )
    except ValueError:
        print("Invalid input. Using default value.")
        num_profiles = 5

    # Initialize the scraper with RocketReach API key
    scraper = LinkedInScraper(email, password, rr_api_key=rr_api_key)

    # If browser method is selected, force fallback mode
    if not use_api:
        scraper.use_browser_fallback = True

    # Define search parameters
    search_term = input("Enter search term: ")
    location = input("Enter location (optional): ") or None
    current_company = input("Enter current company (optional): ") or None
    past_company = input("Enter past company (optional): ") or None

    search_term = search_term.strip().lower()

    print(f"\nSearching for '{search_term}' on LinkedIn...")
    print(
        f"Will visit up to {num_profiles} profiles, automatically navigating through pages as needed."
    )
    if use_api and rr_api_key:
        print("Profiles will be enriched with RocketReach API data.")
    else:
        print("Profiles will be enriched with RocketReach browser automation data.")
    print("This may take a few minutes. Please wait...\n")

    try:
        # Run the scraping process with pagination
        scraper.setup_driver()
        if scraper.login():
            # Use the enhanced visit_profiles method (automatically handles pagination)
            scraper.visit_profiles(
                search_term,
                location=location,
                num_profiles=num_profiles,
                current_company=current_company,
                past_company=past_company,
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
