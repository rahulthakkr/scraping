import os
import time

import pandas as pd
import rocketreach
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from rocketreach_browser import RocketReachBrowser

SUPPORTED_LOCATIONS = {
    "dubai": 106204383,
    "united_states": 103644278,
    "united_kingdom": 101165590,
    "canada": 101174742,
    "australia": 101452733,
    "india": 102713980,
    "london": 90009496,
}

SUPPORTED_COMPANIES = {
    "google": "1441",
    "meta": "10667",
    "amazon": "1586",
    "apple": "162479",
    "microsoft": "1035",
}


class LinkedInScraper:
    def __init__(self, email, password, rr_api_key=None):
        """Initialize the LinkedIn scraper with login credentials and optional RocketReach API key."""
        self.email = email
        self.password = password
        self.driver = None
        self.data = []
        self.rr_api_key = rr_api_key
        self.rr_client = None
        self.current_profile_name = "N/A"  # Initialize current profile name
        self.rr_browser = None  # Initialize RocketReach browser
        self.use_browser_fallback = False  # Flag to use browser fallback instead of API

        # Initialize RocketReach client if API key is provided
        if self.rr_api_key:
            try:
                self.rr_client = rocketreach.Gateway(api_key=self.rr_api_key)
                print("RocketReach client initialized successfully")
            except Exception as e:
                print(f"Error initializing RocketReach client: {e}")
                self.rr_client = None
                # Set flag to use browser fallback
                self.use_browser_fallback = True
                print("Will use browser-based RocketReach lookup as fallback")

    def setup_driver(self):
        """Set up the Chrome WebDriver."""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Start maximized
        chrome_options.add_argument("--disable-notifications")  # Disable notifications

        # Initialize Chrome WebDriver with options
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Log in to LinkedIn."""
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)

            # Enter email
            email_field = self.driver.find_element(By.ID, "username")
            email_field.send_keys(self.email)

            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)

            # Click login button
            login_button = self.driver.find_element(
                By.XPATH, "//button[@type='submit']"
            )
            login_button.click()

            # Wait for login to complete
            time.sleep(5)

            # Check if login was successful
            if (
                "feed" in self.driver.current_url
                or "checkpoint" in self.driver.current_url
            ):
                print("Login successful!")
                return True
            else:
                print("Login failed. Please check your credentials.")
                return False

        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def lookup_rocketreach(self, linkedin_url):
        """
        Look up a LinkedIn profile on RocketReach to get additional information.

        Args:
            linkedin_url: The LinkedIn profile URL or contact info URL

        Returns:
            Dictionary with RocketReach data or None if lookup failed
        """
        # First check if we should use browser-based lookup (API exhausted or not available)
        if self.use_browser_fallback:
            return self.lookup_rocketreach_browser(linkedin_url)

        if not self.rr_client:
            print("RocketReach client not initialized. Skipping lookup.")
            # Try browser-based lookup as fallback
            return self.lookup_rocketreach_browser(linkedin_url)

        try:
            # Perform the lookup
            lookup_result = self.rr_client.person.lookup(linkedin_url=linkedin_url)

            if hasattr(lookup_result, "person") and lookup_result.person:
                print(f"RocketReach lookup successful for {linkedin_url}")
                return lookup_result.person.to_dict()
            else:
                print(f"No RocketReach data found for {linkedin_url}")

                # Check for API credits exhausted error
                if (
                    hasattr(lookup_result, "error")
                    and "credits" in str(lookup_result.error).lower()
                ):
                    print("API credits exhausted. Switching to browser-based lookup.")
                    self.use_browser_fallback = True
                    return self.lookup_rocketreach_browser(linkedin_url)

                # Try an alternative approach - lookup by name if available
                if (
                    hasattr(self, "current_profile_name")
                    and self.current_profile_name != "N/A"
                ):
                    print(f"Trying to look up by name: {self.current_profile_name}")
                    try:
                        name_lookup = self.rr_client.person.search(
                            name=self.current_profile_name, limit=1
                        )
                        if (
                            hasattr(name_lookup, "people")
                            and name_lookup.people
                            and len(name_lookup.people) > 0
                        ):
                            print(f"Found person by name: {name_lookup.people[0]}")
                            return name_lookup.people[0].to_dict()
                    except Exception as e:
                        if "credits" in str(e).lower():
                            print(
                                "API credits exhausted. Switching to browser-based lookup."
                            )
                            self.use_browser_fallback = True
                            return self.lookup_rocketreach_browser(linkedin_url)
                        print(f"Error looking up by name: {e}")
                        return {}

                return {}
        except Exception as e:
            if "credits" in str(e).lower():
                print("API credits exhausted. Switching to browser-based lookup.")
                self.use_browser_fallback = True
                return self.lookup_rocketreach_browser(linkedin_url)
            print(f"Error looking up on RocketReach: {e}")
            return {}

    def lookup_rocketreach_browser(self, linkedin_url):
        """
        Look up a LinkedIn profile on RocketReach using browser automation.
        This is used as a fallback when API credits are exhausted.

        Args:
            linkedin_url: The LinkedIn profile URL

        Returns:
            Dictionary with RocketReach data or empty dict if lookup failed
        """
        try:
            # Initialize the RocketReach browser if not already done
            if not self.rr_browser:
                print("Initializing RocketReach browser automation...")
                self.rr_browser = RocketReachBrowser()
                self.rr_browser.setup_driver()

                # Try to login
                if not self.rr_browser.login():
                    print(
                        "Failed to login to RocketReach via browser. Cannot perform lookup."
                    )
                    return {}

            # Search for the LinkedIn URL on RocketReach
            print(
                f"Searching for LinkedIn URL on RocketReach via browser: {linkedin_url}"
            )
            profile_data = self.rr_browser.search_by_linkedin_url(linkedin_url)

            if profile_data:
                print(
                    f"Successfully found profile via browser: {profile_data.get('name', 'Unknown')}"
                )
                return profile_data
            else:
                print(f"Could not find profile via browser for: {linkedin_url}")
                return {}

        except Exception as e:
            print(f"Error during browser-based RocketReach lookup: {e}")
            return {}

    def extract_contact_info_url(self, profile_url):
        """
        Click on the 'Contact info' button and extract the contact info URL.

        Args:
            profile_url: The LinkedIn profile URL

        Returns:
            Tuple of (contact_info_url, email, phone, website) or (None, None, None, None) if not found
        """
        try:
            # Make sure we're on the profile page
            if profile_url not in self.driver.current_url:
                self.driver.get(profile_url)
                time.sleep(3)

            # Try different patterns for the contact info button
            contact_info_button = None
            contact_info_patterns = [
                "//a[@id='top-card-text-details-contact-info' and contains(@class, 'ember-view')]",
                "//a[contains(text(), 'Contact info')]",
                "//a[contains(@class, 'link-without-visited-state') and contains(text(), 'Contact info')]",
                "//a[contains(@href, '/overlay/contact-info/')]",
            ]

            for pattern in contact_info_patterns:
                try:
                    contact_info_button = self.driver.find_element(By.XPATH, pattern)
                    if contact_info_button:
                        print(f"Found contact info button using pattern: {pattern}")
                        break
                except:
                    continue

            if not contact_info_button:
                print("Could not find contact info button")
                return None, None, None, None

            # Get the href attribute before clicking
            contact_info_url = contact_info_button.get_attribute("href")
            contact_info_url = contact_info_url.split("con")
            print(f"Contact info URL: {contact_info_url}")

            # Click the button to open contact info overlay
            contact_info_button.click()
            time.sleep(3)  # Wait for overlay to load

            linkedin_url = None
            try:
                linkedin_url = self.driver.find_element(
                    By.XPATH, "//a[contains(@href, 'linkedin.com/in/')]"
                )
                linkedin_url = linkedin_url.get_attribute("href")
            except:
                pass

            # Close the overlay by pressing Escape
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)

            return linkedin_url

        except Exception as e:
            print(f"Error extracting contact info: {e}")
            return None, None, None, None

    def scrape_profile(self, profile_url):
        """
        Visit a profile and extract basic information.

        Args:
            profile_url: The LinkedIn profile URL to scrape
            already_on_page: If True, assumes we're already on the profile page
        """
        try:
            print(f"Visiting profile: {profile_url}")
            self.driver.get(profile_url)
            time.sleep(5)  # Increased wait time for profile to load

            # Extract basic profile information using multiple possible selectors
            name = "N/A"
            headline = "N/A"
            location = "N/A"
            about = "N/A"
            current_position = "N/A"

            # Name - try multiple patterns
            name_patterns = [
                "//h1[@class='text-heading-xlarge inline t-24 v-align-middle break-words']",
                "//h1[contains(@class, 'text-heading-xlarge')]",
                "//h1[contains(@class, 'pv-top-card-section__name')]",
                "//h1",
            ]

            for pattern in name_patterns:
                try:
                    name_element = self.driver.find_element(By.XPATH, pattern)
                    name = name_element.text.strip()
                    if name:
                        break
                except:
                    continue

            # Store the current profile name for use in RocketReach lookup
            self.current_profile_name = name

            # Headline - try multiple patterns
            headline_patterns = [
                "//div[@class='text-body-medium break-words']",
                "//div[contains(@class, 'pv-top-card-section__headline')]",
                "//div[contains(@class, 'text-body-medium')]",
            ]

            for pattern in headline_patterns:
                try:
                    headline_element = self.driver.find_element(By.XPATH, pattern)
                    headline = headline_element.text.strip()
                    if headline:
                        break
                except:
                    continue

            # Location - try multiple patterns
            location_patterns = [
                "//span[@class='text-body-small inline t-black--light break-words']",
                "//span[contains(@class, 'pv-top-card-section__location')]",
                "//span[contains(@class, 'text-body-small') and contains(@class, 'break-words')]",
            ]

            for pattern in location_patterns:
                try:
                    location_element = self.driver.find_element(By.XPATH, pattern)
                    location = location_element.text.strip()
                    if location:
                        break
                except:
                    continue

            # About section - try multiple patterns
            about_patterns = [
                "//div[@class='display-flex ph5 pv3']//span[@aria-hidden='true']",
                "//section[contains(@class, 'pv-about-section')]//p",
                "//div[contains(@class, 'display-flex ph5')]//span[@aria-hidden='true']",
            ]

            for pattern in about_patterns:
                try:
                    about_element = self.driver.find_element(By.XPATH, pattern)
                    about = about_element.text.strip()
                    if about:
                        break
                except:
                    continue

            # Current position - try multiple patterns
            position_patterns = [
                "//section[@id='experience']//li[1]//span[@aria-hidden='true']",
                "//section[contains(@class, 'experience-section')]//li[1]//h3",
                "//section[contains(@id, 'experience')]//li[1]//span[@aria-hidden='true']",
            ]

            for pattern in position_patterns:
                try:
                    position_element = self.driver.find_element(By.XPATH, pattern)
                    current_position = position_element.text.strip()
                    if current_position:
                        break
                except:
                    continue

            # Look up additional information from RocketReach
            rr_data = None
            if self.rr_client:
                print(f"Looking up profile on RocketReach: {profile_url}")
                rr_data = self.lookup_rocketreach(profile_url)

            try:
                valid_emails = [
                    email["email"]
                    for email in rr_data["emails"]
                    if email["smtp_valid"] == "valid"
                    or email["smtp_valid"] == "inconclusive"
                ]
                current_role = rr_data.get("current_role", "N/A")
                current_employer = rr_data.get("current_employer", "N/A")
            except:
                valid_emails = []
                current_role = "N/A"
                current_employer = "N/A"

            # Convert RocketReach data to JSON string for storage
            additional_info = rr_data or "N/A"

            # Store the extracted data
            profile_data = {
                "Name": name,
                "Headline": headline,
                "Location": location,
                "About": sanitize_text_for_csv(about),
                "Valid Emails": valid_emails,
                "Current Position": current_role,
                "Current Employer": current_employer,
                "Profile URL": profile_url,
                "Additional Info": additional_info,  # Add RocketReach data
            }

            print(f"Scraped profile: {name}")
            return profile_data

        except Exception as e:
            print(f"Error scraping profile {profile_url}: {e}")

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
        # Close the RocketReach browser if it was opened
        if self.rr_browser:
            self.rr_browser.close()

    def visit_profiles(
        self,
        search_term,
        num_profiles=5,
        location=None,
        current_company=None,
        past_company=None,
    ):
        """
        Search for people with the given search term and visit up to the requested number of profiles.
        Skip profiles that are already in the CSV file. Will automatically navigate to next pages
        as needed until reaching the requested number of new profiles.

        Args:
            search_term: The keyword to search for on LinkedIn
            num_profiles: Maximum number of profiles to visit
            location: The location to search for
        """
        try:
            #  Build the search URL with optional location filter
            base_url = "https://www.linkedin.com/search/results/people/?keywords="
            search_url = f"{base_url}{search_term.replace(' ', '%20')}"

            # Add location filter if specified
            if location:
                location_id = SUPPORTED_LOCATIONS.get(
                    location.lower().replace(" ", "_")
                )
                assert location_id, f"Location {location} not supported"
                search_url += f"&geoUrn=%5B%22{location_id}%22%5D"
                print(f"Adding location filter: {location}")

            if current_company:
                current_company_id = SUPPORTED_COMPANIES.get(
                    current_company.lower().replace(" ", "_")
                )
                assert current_company_id, f"Company {current_company} not supported"
                search_url += f"&currentCompany=%5B%22{current_company_id}%22%5D"
                print(f"Adding current company filter: {current_company}")

            if past_company:
                past_company_id = SUPPORTED_COMPANIES.get(
                    past_company.lower().replace(" ", "_")
                )
                assert past_company_id, f"Company {past_company} not supported"
                search_url += f"&pastCompany=%5B%22{past_company_id}%22%5D"
                print(f"Adding past company filter: {past_company}")
            print(
                f"Searching for '{search_term}' on LinkedIn"
                + (f" in {location}" if location else "")
            )
            print(
                f"Will visit up to {num_profiles} unique profiles, automatically navigating through pages as needed"
            )

            # Create filename for this search
            filename = f"linkedin_profiles_{search_term.replace(' ', '_')}.csv"

            if os.path.exists(filename):
                try:
                    existing_df = pd.read_csv(filename)
                    existing_profiles = existing_df["Profile URL"].tolist()
                    self.existing_profiles = set(existing_profiles)
                    print(
                        f"Found {len(self.existing_profiles)} existing profiles in CSV. Will skip these profiles."
                    )
                except Exception as e:
                    print(f"Error reading existing CSV: {e}")
            else:
                print("No existing profiles found. Creating new CSV.")
                self.existing_profiles = set()

            # Initialize counters
            profiles_to_visit = []
            page_number = 0

            # We advance pages here.
            while len(profiles_to_visit) < num_profiles:
                page_number += 1
                visit_url = search_url + f"&page={page_number}"
                self.driver.get(visit_url)
                print(f"\n--- Fetching profiles from page {page_number} ---")

                time.sleep(5)  # Wait time for page to load

                # finding the pattern for the profile links
                profile_links = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'a[href*="linkedin.com/in/"][data-test-app-aware-link]',
                )

                if (
                    len(profile_links) == 0
                ):  # If the current page has no profiles left then no point in checking for the next page.
                    print(f"No profiles found on page {page_number}. Exiting.")
                    self.close()
                    return

                profile_links = [
                    link.get_attribute("href")
                    for link in profile_links
                    if link.get_attribute("href")
                ]
                profile_links = [
                    link.split("?")[0]
                    for link in profile_links
                    if not link.split("/in/")[1].startswith("ACoAA")
                ]

                profile_links = set(profile_links)

                profile_links = [
                    link for link in profile_links if link not in self.existing_profiles
                ]

                print(
                    f"Found {len(profile_links)} new profile URLs on page {page_number}"
                )
                if profile_links:
                    profiles_to_visit.extend(profile_links)

            # Once we have the profiles to visit, we can start scraping them
            for profile_url in profiles_to_visit:
                try:
                    profile_data = self.scrape_profile(profile_url)
                    profile_data = pd.DataFrame([profile_data])
                    if not os.path.exists(filename):
                        profile_data.to_csv(filename, index=False)
                    else:
                        profile_data.to_csv(
                            filename, mode="a", header=False, index=False
                        )
                except Exception as e:
                    print(f"Error scraping profile {profile_url}: {e}")
        except Exception as e:
            print(f"Error: {e}")
            self.close()
            return

    def debug_page_source(self, filename):
        """Save the current page source to a file for debugging."""
        try:
            page_source = self.driver.page_source
            with open(filename, "w", encoding="utf-8") as f:
                f.write(page_source)
            print(f"Saved page source to {filename}")
        except Exception as e:
            print(f"Error saving page source: {e}")


def sanitize_text_for_csv(text):
    """
    Sanitize text to prevent CSV formatting issues.

    Args:
        text: The text to sanitize

    Returns:
        Sanitized text safe for CSV inclusion
    """
    if not text or text == "N/A":
        return text

    # Replace newlines with space
    text = text.replace("\n", " ").replace("\r", " ")

    # Handle quotes by doubling them (CSV standard)
    text = text.replace('"', '""')

    # If text contains commas, quotes, or other special chars, wrap in quotes
    if "," in text or '"' in text or "\t" in text:
        text = f'"{text}"'

    return text
